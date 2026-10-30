#!/usr/bin/env python3
"""
Check developer.ui.com for UniFi API releases newer than the versions the library pins.

For each product, the latest version is the one ``https://developer.ui.com/<slug>``
redirects to. The pinned version is the ``*_SPEC_VERSION`` constant in
``src/unifi_official_api/const.py``. When the latest version is newer, the script
downloads both OpenAPI documents and compares them after removing documentation-only
content (descriptions, examples, titles, tags, operation IDs and ``x-`` extensions).

An issue is opened only when that comparison finds a real change, so a version bump
that ships an identical spec stays silent. The issue is labeled ``bug`` when the
change can break existing callers (a removed operation, field or enum value, a
changed type, or a newly required request input) and ``enhancement`` otherwise.

Each issue carries a hidden marker with the product and version. A version that
already has an issue, open or closed, is never reported again. When a newer version
arrives while an older issue is still open, that issue is updated instead of opening
a second one.

The script uses only the standard library. It talks to GitHub through the ``gh`` CLI,
which needs ``GH_TOKEN`` and ``GITHUB_REPOSITORY`` in the environment.

Usage:
    python script/check_api_updates.py            # report only
    python script/check_api_updates.py --apply    # also open or update issues
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONST_PATH = ROOT / "src" / "unifi_official_api" / "const.py"
FIXTURES_DIR = ROOT / "tests" / "fixtures"
DEVELOPER_SITE = "https://developer.ui.com"
USER_AGENT = (
    "unifi-official-api-update-monitor (+https://github.com/tinkerologie/unifi-official-api)"
)

TRACKING_LABEL = "upstream-api"
# ``confirmed`` keeps the stale workflow from closing an issue before it is implemented.
EXTRA_LABELS = ("confirmed",)
MARKER_RE = re.compile(
    r"<!-- unifi-api-monitor: product=(?P<product>[a-z-]+) version=(?P<version>[0-9.]+) -->"
)
VERSION_RE = re.compile(r"^\d+(?:\.\d+)*$")
MAX_DETAIL_LINES = 150
MAX_BODY_CHARS = 60_000


@dataclass(frozen=True)
class Product:
    """A UniFi API published on developer.ui.com."""

    slug: str
    name: str
    constant: str


PRODUCTS: tuple[Product, ...] = (
    Product("network", "UniFi Network API", "NETWORK_SPEC_VERSION"),
    Product("protect", "UniFi Protect API", "PROTECT_SPEC_VERSION"),
    Product("innerspace", "UniFi InnerSpace API", "INNERSPACE_SPEC_VERSION"),
    Product("mobility", "UniFi Mobility API", "MOBILITY_SPEC_VERSION"),
    Product("site-manager", "UniFi Site Manager API", "SITE_MANAGER_SPEC_VERSION"),
    Product("carrier-fabric", "UniFi Carrier Fabric API", "CARRIER_FABRIC_SPEC_VERSION"),
)

# ---------------------------------------------------------------------------
# Spec normalization and diffing
# ---------------------------------------------------------------------------

# Keywords that only affect rendered documentation.
ANNOTATION_KEYS = frozenset(
    {
        "description",
        "summary",
        "example",
        "examples",
        "externalDocs",
        "title",
        "tags",
        "operationId",
    }
)
# Keys whose children are user-chosen names, not keywords. A property called
# ``description`` must survive normalization.
NAME_MAP_KEYS = frozenset(
    {
        "properties",
        "patternProperties",
        "$defs",
        "definitions",
        "schemas",
        "parameters",
        "requestBodies",
        "responses",
        "headers",
        "content",
        "paths",
        "variables",
        "securitySchemes",
        "dependentSchemas",
    }
)
# Lists whose order carries no meaning.
UNORDERED_LIST_KEYS = frozenset({"required", "enum", "type"})
HTTP_METHODS = ("get", "put", "post", "delete", "patch", "head", "options", "trace")


def _sort_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def normalize(node: Any, *, name_map: bool = False, key: str | None = None) -> Any:
    """Return ``node`` without documentation-only content, in a stable shape."""
    if isinstance(node, dict):
        if name_map:
            return {k: normalize(v) for k, v in node.items()}
        out: dict[str, Any] = {}
        for k, v in node.items():
            if k in ANNOTATION_KEYS or k.startswith("x-") or k == "info":
                continue
            out[k] = normalize(v, name_map=k in NAME_MAP_KEYS and isinstance(v, dict), key=k)
        return out
    if key == "type" and isinstance(node, str):
        node = [node]  # "string" and ["string"] mean the same; keep one shape
    if isinstance(node, list):
        if key in UNORDERED_LIST_KEYS and all(not isinstance(i, dict | list) for i in node):
            return sorted({_sort_key(i): i for i in node}.values(), key=_sort_key)
        if node and all(isinstance(i, dict) and set(i) == {"$ref"} for i in node):
            # oneOf/anyOf/allOf of references: key by target so one new variant is one change.
            return {i["$ref"]: {} for i in node}
        if node and all(isinstance(i, dict) and "name" in i and "in" in i for i in node):
            return {f"{i['in']}:{i['name']}": normalize(i) for i in node}
        return [normalize(i) for i in node]
    return node


@dataclass(frozen=True)
class Change:
    """One leaf-level difference between two normalized documents."""

    kind: str  # "added", "removed" or "changed"
    path: tuple[str, ...]
    old: Any = None
    new: Any = None


def diff(old: Any, new: Any, path: tuple[str, ...] = ()) -> list[Change]:
    """Return the leaf-level changes from ``old`` to ``new``."""
    if isinstance(old, dict) and isinstance(new, dict):
        changes: list[Change] = []
        for k in sorted(set(old) | set(new)):
            if k not in old:
                changes.append(Change("added", (*path, k), new=new[k]))
            elif k not in new:
                changes.append(Change("removed", (*path, k), old=old[k]))
            else:
                changes.extend(diff(old[k], new[k], (*path, k)))
        return changes
    is_scalar_list = (
        isinstance(old, list)
        and isinstance(new, list)
        and all(not isinstance(i, dict | list) for i in [*old, *new])
    )
    if is_scalar_list and path and path[-1] in UNORDERED_LIST_KEYS:
        added = [Change("added", path, new=i) for i in new if i not in old]
        removed = [Change("removed", path, old=i) for i in old if i not in new]
        return removed + added
    if old != new:
        return [Change("changed", path, old=old, new=new)]
    return []


def _collect_refs(node: Any, refs: set[str]) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            refs.add(ref)
        for k, v in node.items():
            if isinstance(k, str) and k.startswith("#/"):
                refs.add(k)  # normalized oneOf/anyOf keys
            _collect_refs(v, refs)
    elif isinstance(node, list):
        for i in node:
            _collect_refs(i, refs)


def request_schema_names(spec: dict[str, Any]) -> set[str]:
    """Return the component schemas reachable from any operation's request body."""
    schemas = spec.get("components", {}).get("schemas", {})
    pending: set[str] = set()
    for item in spec.get("paths", {}).values():
        for method in HTTP_METHODS:
            body = item.get(method, {}).get("requestBody") if isinstance(item, dict) else None
            if body:
                _collect_refs(body, pending)
    prefix = "#/components/schemas/"
    seen: set[str] = set()
    while pending:
        ref = pending.pop()
        name = ref.removeprefix(prefix)
        if not ref.startswith(prefix) or name in seen or name not in schemas:
            continue
        seen.add(name)
        _collect_refs(schemas[name], pending)
    return seen


@dataclass
class SpecDiff:
    """Differences between the pinned and latest spec of one product."""

    added_operations: list[str] = field(default_factory=list)
    removed_operations: list[str] = field(default_factory=list)
    operation_changes: dict[str, list[Change]] = field(default_factory=dict)
    added_schemas: list[str] = field(default_factory=list)
    removed_schemas: list[str] = field(default_factory=list)
    schema_changes: dict[str, list[Change]] = field(default_factory=dict)
    other_changes: list[Change] = field(default_factory=list)
    breaking: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (
            self.added_operations
            or self.removed_operations
            or self.operation_changes
            or self.added_schemas
            or self.removed_schemas
            or self.schema_changes
            or self.other_changes
        )


def _operations(spec: dict[str, Any]) -> dict[str, Any]:
    ops: dict[str, Any] = {}
    for path, item in spec.get("paths", {}).items():
        if not isinstance(item, dict):
            continue
        shared = item.get("parameters", {})
        for method in HTTP_METHODS:
            if method in item:
                op = dict(item[method])
                if shared:
                    op["parameters"] = {**shared, **op.get("parameters", {})}
                ops[f"{method.upper()} {path}"] = op
    return ops


def _breaking_reason(change: Change, *, request_side: bool) -> str | None:
    """Return why ``change`` can break existing callers, or ``None``."""
    path = change.path
    last = path[-1] if path else ""
    parent = path[-2] if len(path) > 1 else ""
    if change.kind == "removed" and parent == "properties":
        return f"field `{last}` removed"
    if change.kind == "removed" and last == "enum":
        return f"enum value `{change.old}` removed at `{_fmt_path(path)}`"
    if change.kind == "removed" and last == "type":
        return f"type `{change.old}` no longer allowed at `{_fmt_path(path[:-1]) or '(root)'}`"
    if change.kind == "added" and last == "required" and request_side:
        return f"request field `{change.new}` is now required"
    if parent == "parameters" and change.kind == "removed":
        return f"parameter `{last}` removed"
    is_new_param = parent == "parameters" and change.kind == "added"
    if is_new_param and isinstance(change.new, dict) and change.new.get("required"):
        return f"new required parameter `{last}`"
    if len(path) > 2 and path[-3] == "parameters" and last == "required":
        if change.kind == "changed" and change.new is True:
            return f"parameter `{path[-2]}` is now required"
        if change.kind == "added" and change.new is True:
            return f"parameter `{path[-2]}` is now required"
    return None


def compare_specs(old_spec: dict[str, Any], new_spec: dict[str, Any]) -> SpecDiff:
    """Compare two raw OpenAPI documents, ignoring documentation-only content."""
    old, new = normalize(old_spec), normalize(new_spec)
    result = SpecDiff()

    old_ops, new_ops = _operations(old), _operations(new)
    result.added_operations = sorted(set(new_ops) - set(old_ops))
    result.removed_operations = sorted(set(old_ops) - set(new_ops))
    result.breaking.extend(f"operation `{op}` removed" for op in result.removed_operations)
    for op in sorted(set(old_ops) & set(new_ops)):
        changes = diff(old_ops[op], new_ops[op])
        if changes:
            result.operation_changes[op] = changes
            for change in changes:
                reason = _breaking_reason(change, request_side="requestBody" in change.path)
                if reason:
                    result.breaking.append(f"`{op}`: {reason}")

    old_schemas = old.get("components", {}).get("schemas", {})
    new_schemas = new.get("components", {}).get("schemas", {})
    request_schemas = request_schema_names(new_spec)
    result.added_schemas = sorted(set(new_schemas) - set(old_schemas))
    result.removed_schemas = sorted(set(old_schemas) - set(new_schemas))
    result.breaking.extend(f"schema `{name}` removed" for name in result.removed_schemas)
    for name in sorted(set(old_schemas) & set(new_schemas)):
        changes = diff(old_schemas[name], new_schemas[name])
        if changes:
            result.schema_changes[name] = changes
            for change in changes:
                reason = _breaking_reason(change, request_side=name in request_schemas)
                if reason:
                    result.breaking.append(f"schema `{name}`: {reason}")

    def _rest(spec: dict[str, Any]) -> dict[str, Any]:
        rest = {k: v for k, v in spec.items() if k not in ("paths", "openapi")}
        components = {k: v for k, v in rest.get("components", {}).items() if k != "schemas"}
        if components:
            rest["components"] = components
        else:
            rest.pop("components", None)
        return rest

    result.other_changes = diff(_rest(old), _rest(new))
    return result


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _fmt_path(path: tuple[str, ...]) -> str:
    return "/".join(path)


def _fmt_value(value: Any, limit: int = 140) -> str:
    text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    text = text if len(text) <= limit else text[: limit - 1] + "…"
    return text.replace("`", "'")


def _fmt_change(change: Change) -> str:
    where = f"`{_fmt_path(change.path) or '(root)'}`"
    if change.kind == "added":
        return f"  - added {where}: `{_fmt_value(change.new)}`"
    if change.kind == "removed":
        return f"  - removed {where}: `{_fmt_value(change.old)}`"
    return f"  - changed {where}: `{_fmt_value(change.old)}` → `{_fmt_value(change.new)}`"


def render_details(spec_diff: SpecDiff) -> list[str]:
    """Return the Markdown lines that describe each change."""
    lines: list[str] = []

    def section(title: str, items: list[str]) -> None:
        if items:
            lines.extend(["", f"### {title}", "", *items])

    section("Breaking changes", [f"- {b}" for b in spec_diff.breaking])
    section("New operations", [f"- `{op}`" for op in spec_diff.added_operations])
    section("Removed operations", [f"- `{op}`" for op in spec_diff.removed_operations])
    changed_ops: list[str] = []
    for op, op_changes in spec_diff.operation_changes.items():
        changed_ops.append(f"- `{op}`")
        changed_ops.extend(_fmt_change(c) for c in op_changes)
    section("Changed operations", changed_ops)
    section("New schemas", [f"- `{name}`" for name in spec_diff.added_schemas])
    section("Removed schemas", [f"- `{name}`" for name in spec_diff.removed_schemas])
    changed_schemas: list[str] = []
    for name, schema_changes in spec_diff.schema_changes.items():
        changed_schemas.append(f"- `{name}`")
        changed_schemas.extend(_fmt_change(c) for c in schema_changes)
    section("Changed schemas", changed_schemas)
    section("Other changes", [_fmt_change(c).lstrip() for c in spec_diff.other_changes])

    if len(lines) > MAX_DETAIL_LINES:
        hidden = len(lines) - MAX_DETAIL_LINES
        lines = [
            *lines[:MAX_DETAIL_LINES],
            "",
            f"_…and {hidden} more lines. Diff the two specs for the rest._",
        ]
    return lines


@dataclass(frozen=True)
class Report:
    """A product whose latest spec differs from the pinned one."""

    product: Product
    pinned: str
    latest: str
    docs_url: str
    spec_diff: SpecDiff

    @property
    def label(self) -> str:
        return "bug" if self.spec_diff.breaking else "enhancement"

    @property
    def title(self) -> str:
        if self.spec_diff.breaking:
            return f"[Bug]: {self.product.name} {self.latest} has breaking changes"
        return f"[Enhancement]: Support {self.product.name} {self.latest}"

    @property
    def marker(self) -> str:
        return f"<!-- unifi-api-monitor: product={self.product.slug} version={self.latest} -->"

    def body(self) -> str:
        p, d = self.product, self.spec_diff
        spec_url = f"{DEVELOPER_SITE}/{p.slug}/v{self.latest}/openapi.json"
        pinned_url = f"{DEVELOPER_SITE}/{p.slug}/v{self.pinned}/openapi.json"
        summary = (
            f"{len(d.added_operations)} new and {len(d.removed_operations)} removed operations, "
            f"{len(d.operation_changes)} changed operations, "
            f"{len(d.added_schemas)} new, {len(d.removed_schemas)} removed and "
            f"{len(d.schema_changes)} changed schemas, "
            f"{len(d.breaking)} breaking changes."
        )
        lines = [
            self.marker,
            "",
            f"UniFi published **{p.name} {self.latest}** on developer.ui.com. "
            f"The library pins **{self.pinned}** "
            f"(`{p.constant}` in `src/unifi_official_api/const.py`).",
            "",
            "| | Version | OpenAPI |",
            "|---|---|---|",
            f"| Pinned | {self.pinned} | [openapi.json]({pinned_url}) |",
            f"| Latest | {self.latest} | [openapi.json]({spec_url}) |",
            "",
            f"Docs: {self.docs_url}",
            "",
            f"**Summary:** {summary}",
            "",
            "The comparison ignores documentation-only changes (descriptions, examples, titles, "
            "tags, operation IDs and `x-` extensions).",
            *render_details(d),
            "",
            "### Next steps",
            "",
            "- Review the changes against the library's models and endpoints.",
            f"- Bump `{p.constant}` to `{self.latest}`. Where a spec fixture is vendored under "
            "`tests/fixtures/`, replace it with the new document in the same change.",
            "",
            "_Opened by the UniFi API update monitor "
            "(`.github/workflows/api-update-monitor.yml`)._",
        ]
        body = "\n".join(lines)
        if len(body) > MAX_BODY_CHARS:
            body = body[:MAX_BODY_CHARS] + "\n\n_Truncated. Diff the two specs for the rest._"
        return body


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


class FetchError(Exception):
    """developer.ui.com did not return what the monitor expects."""


def _open(url: str, attempts: int = 3) -> tuple[str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.geturl(), response.read()
        except urllib.error.HTTPError as err:
            if err.code < 500 and err.code != 429:
                raise FetchError(f"{url}: HTTP {err.code}") from err
            error = err
        except (urllib.error.URLError, TimeoutError) as err:
            error = err
        if attempt < attempts:
            time.sleep(5 * attempt)
    raise FetchError(f"{url}: {error}")


def fetch_latest(product: Product) -> tuple[str, str]:
    """Return the latest version of ``product`` and the docs URL it resolves to."""
    final_url, _ = _open(f"{DEVELOPER_SITE}/{product.slug}")
    match = re.match(
        rf"^{re.escape(DEVELOPER_SITE)}/{re.escape(product.slug)}/v([0-9.]+)(?:/|$)", final_url
    )
    if not match or not VERSION_RE.match(match.group(1)):
        raise FetchError(f"{product.slug}: no version in redirect target {final_url}")
    return match.group(1), final_url


def fetch_spec(product: Product, version: str) -> dict[str, Any]:
    """Return the OpenAPI document of ``product`` at ``version``."""
    fixture = FIXTURES_DIR / f"{product.slug.replace('-', '_')}_openapi_{version}.json"
    if fixture.is_file():
        raw = fixture.read_bytes()
    else:
        _, raw = _open(f"{DEVELOPER_SITE}/{product.slug}/v{version}/openapi.json")
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as err:
        raise FetchError(f"{product.slug} {version}: openapi.json is not JSON") from err
    if (
        not isinstance(spec, dict)
        or "openapi" not in spec
        or not isinstance(spec.get("paths"), dict)
    ):
        raise FetchError(f"{product.slug} {version}: openapi.json is not an OpenAPI document")
    return spec


def read_pinned_versions(const_path: Path = CONST_PATH) -> dict[str, str]:
    """Return the string constants of ``const.py`` without importing the package."""
    values: dict[str, str] = {}
    for node in ast.parse(const_path.read_text()).body:
        target: ast.expr | None = node.target if isinstance(node, ast.AnnAssign) else None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        value = node.value if isinstance(node, ast.Assign | ast.AnnAssign) else None
        if (
            isinstance(target, ast.Name)
            and isinstance(value, ast.Constant)
            and isinstance(value.value, str)
        ):
            values[target.id] = value.value
    return values


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


# ---------------------------------------------------------------------------
# Issue planning and GitHub
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrackedIssue:
    """An issue opened by this monitor."""

    number: int
    state: str
    product: str
    version: str
    labels: tuple[str, ...]


@dataclass(frozen=True)
class Action:
    """What to do for one report."""

    kind: str  # "skip", "create" or "update"
    issue: TrackedIssue | None = None
    reason: str = ""


def plan_action(report: Report, issues: list[TrackedIssue]) -> Action:
    """Decide whether ``report`` needs a new issue, an update, or nothing."""
    mine = [i for i in issues if i.product == report.product.slug]
    for issue in mine:
        if issue.version == report.latest:
            return Action(
                "skip", issue, f"#{issue.number} already tracks {report.latest} ({issue.state})"
            )
    open_issues = [i for i in mine if i.state == "open"]
    if open_issues:
        newest = max(open_issues, key=lambda i: version_tuple(i.version))
        if version_tuple(newest.version) > version_tuple(report.latest):
            return Action("skip", newest, f"#{newest.number} already tracks newer {newest.version}")
        return Action("update", newest, f"#{newest.number} tracks older {newest.version}")
    return Action("create", None, "no issue tracks this version")


def _gh(*args: str, stdin: str | None = None) -> str:
    result = subprocess.run(
        ["gh", *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result.stdout


def load_tracked_issues(repo: str) -> list[TrackedIssue]:
    """Return every issue (open or closed) that carries a monitor marker."""
    out = _gh(
        "api",
        "--paginate",
        f"repos/{repo}/issues?labels={TRACKING_LABEL}&state=all&per_page=100",
        "--jq",
        ".[] | select(.pull_request == null) | {number, state, body, labels: [.labels[].name]}",
    )
    issues: list[TrackedIssue] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        match = MARKER_RE.search(item.get("body") or "")
        if match:
            issues.append(
                TrackedIssue(
                    number=item["number"],
                    state=item["state"],
                    product=match.group("product"),
                    version=match.group("version"),
                    labels=tuple(item["labels"]),
                )
            )
    return issues


def ensure_label(repo: str) -> None:
    try:
        _gh("api", f"repos/{repo}/labels/{TRACKING_LABEL}")
    except RuntimeError:
        _gh(
            "label",
            "create",
            TRACKING_LABEL,
            "--repo",
            repo,
            "--color",
            "1D76DB",
            "--description",
            "Change published in an official UniFi API spec",
        )


def apply_action(repo: str, report: Report, action: Action) -> str:
    """Open or update the issue for ``report`` and return its URL or number."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
        handle.write(report.body())
        body_file = handle.name
    try:
        labels = [report.label, TRACKING_LABEL, *EXTRA_LABELS]
        if action.kind == "create":
            args = [
                "issue",
                "create",
                "--repo",
                repo,
                "--title",
                report.title,
                "--body-file",
                body_file,
            ]
            for label in labels:
                args += ["--label", label]
            return _gh(*args).strip()
        assert action.issue is not None
        number = str(action.issue.number)
        args = [
            "issue",
            "edit",
            number,
            "--repo",
            repo,
            "--title",
            report.title,
            "--body-file",
            body_file,
        ]
        for label in labels:
            args += ["--add-label", label]
        stale_type = {"bug", "enhancement"} - {report.label}
        for label in stale_type & set(action.issue.labels):
            args += ["--remove-label", label]
        _gh(*args)
        _gh(
            "issue",
            "comment",
            number,
            "--repo",
            repo,
            "--body",
            f"UniFi published {report.product.name} {report.latest}. This issue now tracks "
            f"{report.latest} instead of {action.issue.version}; the description shows the "
            f"changes since the pinned {report.pinned}.",
        )
        return f"#{number}"
    finally:
        Path(body_file).unlink()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def check_product(product: Product, pinned: str) -> tuple[Report | None, str]:
    """Return a report when ``product`` has a newer spec with real changes, and a status line."""
    latest, docs_url = fetch_latest(product)
    if latest == pinned:
        return None, f"{product.name}: up to date ({pinned})"
    if version_tuple(latest) < version_tuple(pinned):
        return None, f"{product.name}: latest {latest} is older than pinned {pinned}; ignored"
    spec_diff = compare_specs(fetch_spec(product, pinned), fetch_spec(product, latest))
    if spec_diff.is_empty:
        return None, (
            f"{product.name}: {latest} has the same spec as pinned {pinned}; "
            f"no issue needed (bump {product.constant} when convenient)"
        )
    report = Report(product, pinned, latest, docs_url, spec_diff)
    return report, f"{product.name}: {pinned} → {latest}, {report.label}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="open or update GitHub issues")
    parser.add_argument("--show-body", action="store_true", help="print each issue body")
    args = parser.parse_args(argv)

    constants = read_pinned_versions()
    missing = [p.constant for p in PRODUCTS if p.constant not in constants]
    if missing:
        print(f"::error::Missing constants in const.py: {', '.join(missing)}")
        return 1

    reports: list[Report] = []
    status: list[str] = []
    failures = 0
    for product in PRODUCTS:
        try:
            report, line = check_product(product, constants[product.constant])
        except FetchError as err:
            failures += 1
            print(f"::warning::{product.name}: skipped, {err}")
            status.append(f"{product.name}: skipped ({err})")
            continue
        status.append(line)
        if report:
            reports.append(report)

    actions: list[str] = []
    if reports and args.apply:
        repo = os.environ["GITHUB_REPOSITORY"]
        ensure_label(repo)
        issues = load_tracked_issues(repo)
        for report in reports:
            action = plan_action(report, issues)
            if action.kind == "skip":
                actions.append(f"{report.product.name}: {action.reason}")
                continue
            target = apply_action(repo, report, action)
            actions.append(f"{report.product.name}: {action.kind}d {target} ({action.reason})")

    output = ["## UniFi API update check", "", *(f"- {line}" for line in status)]
    if actions:
        output += ["", "### Issues", "", *(f"- {line}" for line in actions)]
    elif reports and not args.apply:
        output += ["", "_Report only: no issues were opened or updated._"]
    text = "\n".join(output)
    print(text)
    if args.show_body:
        for report in reports:
            print(f"\n---\n{report.title}\nlabels: {report.label}\n\n{report.body()}")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")

    # Fail only when nothing could be checked, which points at a site change rather than a blip.
    if failures == len(PRODUCTS):
        print("::error::Every product failed; developer.ui.com may have changed its layout.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
