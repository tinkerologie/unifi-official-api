"""The API update monitor reports real spec changes only, and never the same version twice."""

from __future__ import annotations

import copy
import http.client
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = Path(__file__).parent.parent / "script" / "check_api_updates.py"
FIXTURES = Path(__file__).parent / "fixtures"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_api_updates", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves string annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mon = _load()


def _spec(**schemas: Any) -> dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {
            "/v1/things": {
                "get": {
                    "operationId": "listThings",
                    "parameters": [{"name": "limit", "in": "query", "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ThingCreate"}
                            }
                        }
                    },
                    "responses": {"201": {"description": "Created"}},
                },
            }
        },
        "components": {"schemas": schemas},
    }


def _base() -> dict[str, Any]:
    return _spec(
        Thing={
            "type": "object",
            "description": "A thing.",
            "properties": {
                "id": {"type": "string"},
                "mode": {"type": "string", "enum": ["a", "b"]},
                "description": {"type": "string"},
            },
            "required": ["id"],
        },
        ThingCreate={"type": "object", "properties": {"name": {"type": "string"}}},
    )


def test_documentation_only_changes_are_ignored() -> None:
    old, new = _base(), _base()
    new["info"]["version"] = "2.0.0"
    new["paths"]["/v1/things"]["get"]["operationId"] = "renamed"
    new["paths"]["/v1/things"]["get"]["summary"] = "List things"
    new["components"]["schemas"]["Thing"]["description"] = "Reworded."
    new["components"]["schemas"]["Thing"]["properties"]["id"]["examples"] = ["x"]
    new["components"]["schemas"]["Thing"]["required"] = ["id"]
    new["components"]["schemas"]["Thing"]["properties"]["mode"]["enum"] = ["b", "a"]

    assert mon.compare_specs(old, new).is_empty


def test_property_named_like_a_keyword_is_kept() -> None:
    old, new = _base(), _base()
    del new["components"]["schemas"]["Thing"]["properties"]["description"]

    result = mon.compare_specs(old, new)

    assert result.breaking == ["schema `Thing`: field `description` removed"]


def test_pinned_protect_fixture_matches_itself() -> None:
    spec = json.loads((FIXTURES / "protect_openapi_7.3.70.json").read_text())
    changed = copy.deepcopy(spec)
    changed["info"]["version"] = "7.3.74"

    assert mon.compare_specs(spec, changed).is_empty


@pytest.mark.parametrize(
    ("mutate", "breaking"),
    [
        pytest.param(
            lambda s: s["components"]["schemas"]["Thing"]["properties"].update(
                extra={"type": "boolean"}
            ),
            False,
            id="new-field",
        ),
        pytest.param(
            lambda s: s["components"]["schemas"]["Thing"]["properties"]["mode"]["enum"].append("c"),
            False,
            id="new-enum-value",
        ),
        pytest.param(
            lambda s: s["components"]["schemas"]["Thing"]["required"].append("mode"),
            False,
            id="response-field-now-required",
        ),
        pytest.param(
            lambda s: s["components"]["schemas"]["Thing"]["properties"]["id"].update(
                type=["string", "null"]
            ),
            False,
            id="field-now-nullable",
        ),
        pytest.param(
            lambda s: s["paths"]["/v1/things"].update(delete={"responses": {}}),
            False,
            id="new-operation",
        ),
        pytest.param(
            lambda s: s["components"]["schemas"]["Thing"]["properties"]["mode"]["enum"].remove("b"),
            True,
            id="enum-value-removed",
        ),
        pytest.param(
            lambda s: s["components"]["schemas"]["Thing"]["properties"]["id"].update(
                type="integer"
            ),
            True,
            id="type-changed",
        ),
        pytest.param(
            lambda s: s["components"]["schemas"]["ThingCreate"].update(required=["name"]),
            True,
            id="request-field-now-required",
        ),
        pytest.param(
            lambda s: s["paths"]["/v1/things"].pop("post"),
            True,
            id="operation-removed",
        ),
        pytest.param(
            lambda s: s["paths"]["/v1/things"]["get"]["parameters"].append(
                {"name": "site", "in": "query", "required": True}
            ),
            True,
            id="new-required-parameter",
        ),
        pytest.param(
            lambda s: s["paths"]["/v1/things"]["get"]["parameters"][0].update(required=True),
            True,
            id="parameter-now-required",
        ),
    ],
)
def test_classification(mutate: Any, breaking: bool) -> None:
    old, new = _base(), _base()
    mutate(new)

    result = mon.compare_specs(old, new)

    assert not result.is_empty
    assert bool(result.breaking) is breaking


def _report(version: str = "2.0.0", *, breaking: bool = False) -> Any:
    spec_diff = mon.SpecDiff(added_schemas=["New"], breaking=["x"] if breaking else [])
    return mon.Report(mon.PRODUCTS[0], "1.0.0", version, "https://example.invalid", spec_diff)


def _issue(version: str, state: str = "open", product: str = "network") -> Any:
    return mon.TrackedIssue(1, state, product, version, ("enhancement",))


def test_report_title_label_and_marker() -> None:
    report = _report()
    assert report.label == "enhancement"
    assert report.title.startswith("[Enhancement]: ")
    assert mon.MARKER_RE.search(report.body()).group("version") == "2.0.0"

    assert _report(breaking=True).label == "bug"
    assert _report(breaking=True).title.startswith("[Bug]: ")


@pytest.mark.parametrize(
    ("issues", "kind"),
    [
        pytest.param([], "create", id="no-issue"),
        pytest.param([_issue("2.0.0")], "skip", id="same-version-open"),
        pytest.param([_issue("2.0.0", "closed")], "skip", id="same-version-closed"),
        pytest.param([_issue("1.5.0")], "update", id="older-open"),
        pytest.param([_issue("1.5.0", "closed")], "create", id="older-closed"),
        pytest.param([_issue("3.0.0")], "skip", id="newer-open"),
        pytest.param([_issue("2.0.0", product="protect")], "create", id="other-product"),
    ],
)
def test_plan_action(issues: list[Any], kind: str) -> None:
    assert mon.plan_action(_report(), issues).kind == kind


def test_every_product_has_a_pinned_version() -> None:
    constants = mon.read_pinned_versions()

    for product in mon.PRODUCTS:
        assert mon.VERSION_RE.match(constants[product.constant]), product.constant


def test_shared_parameters_merge_with_mixed_and_empty_lists() -> None:
    old = _base()
    old["paths"]["/v1/things"]["parameters"] = [
        {"$ref": "#/components/parameters/siteId"},
        {"name": "x-trace", "in": "header"},
    ]
    old["paths"]["/v1/things"]["post"]["parameters"] = []
    new = copy.deepcopy(old)
    new["paths"]["/v1/things"]["get"]["parameters"].append({"name": "offset", "in": "query"})

    result = mon.compare_specs(old, new)

    assert list(result.operation_changes) == ["GET /v1/things"]
    assert not result.breaking


def test_open_retries_errors_raised_while_reading_the_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Response:
        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def geturl(self) -> str:
            return "https://developer.ui.com/network/v1.0.0/gettingstarted"

        def read(self) -> bytes:
            return b"{}"

    calls: list[int] = []

    def _urlopen(*_args: object, **_kwargs: object) -> _Response:
        calls.append(1)
        if len(calls) == 1:
            raise http.client.IncompleteRead(b"")
        if len(calls) == 2:
            raise ConnectionResetError
        return _Response()

    monkeypatch.setattr(mon.urllib.request, "urlopen", _urlopen)
    monkeypatch.setattr(mon.time, "sleep", lambda _seconds: None)

    assert mon._open("https://developer.ui.com/network")[1] == b"{}"
    assert len(calls) == 3


def test_open_raises_fetch_error_after_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    def _urlopen(*_args: object, **_kwargs: object) -> None:
        raise ConnectionResetError

    monkeypatch.setattr(mon.urllib.request, "urlopen", _urlopen)
    monkeypatch.setattr(mon.time, "sleep", lambda _seconds: None)

    with pytest.raises(mon.FetchError):
        mon._open("https://developer.ui.com/network")


def _with_union(*alternatives: Any) -> dict[str, Any]:
    spec = _base()
    spec["components"]["schemas"]["ThingCreate"]["properties"]["kind"] = {
        "oneOf": list(alternatives)
    }
    return spec


def test_breaking_change_inside_a_composed_schema_is_a_bug() -> None:
    inline = {"type": "object", "properties": {"value": {"type": "string"}}}
    old = _with_union({"$ref": "#/components/schemas/Thing"}, inline)
    new = copy.deepcopy(old)
    new["components"]["schemas"]["ThingCreate"]["properties"]["kind"]["oneOf"][1]["properties"][
        "value"
    ]["type"] = "integer"

    assert mon.compare_specs(old, new).breaking


def test_reordered_alternatives_are_ignored() -> None:
    inline = {"type": "string"}
    old = _with_union({"$ref": "#/components/schemas/Thing"}, inline)
    new = _with_union(inline, {"$ref": "#/components/schemas/Thing"})

    assert mon.compare_specs(old, new).is_empty


def test_description_beside_a_reference_is_ignored() -> None:
    old = _with_union({"$ref": "#/components/schemas/Thing"})
    new = _with_union({"$ref": "#/components/schemas/Thing", "description": "Docs."})

    assert mon.compare_specs(old, new).is_empty


def test_new_alternative_is_an_enhancement() -> None:
    old = _with_union({"$ref": "#/components/schemas/Thing"})
    new = _with_union({"$ref": "#/components/schemas/Thing"}, {"type": "string"})

    result = mon.compare_specs(old, new)

    assert not result.is_empty
    assert not result.breaking


def test_literal_values_are_not_treated_as_documentation() -> None:
    old, new = _base(), _base()
    old["components"]["schemas"]["Thing"]["properties"]["id"]["const"] = {"description": "a"}
    new["components"]["schemas"]["Thing"]["properties"]["id"]["const"] = {"description": "b"}

    assert not mon.compare_specs(old, new).is_empty


@pytest.mark.parametrize("keyword", ["enum", "type"])
def test_removing_a_whole_restriction_is_not_breaking(keyword: str) -> None:
    old, new = _base(), _base()
    del new["components"]["schemas"]["Thing"]["properties"]["mode"][keyword]

    result = mon.compare_specs(old, new)

    assert not result.is_empty
    assert not result.breaking


def test_first_required_parameter_is_a_bug() -> None:
    old, new = _base(), _base()
    new["paths"]["/v1/things"]["post"]["parameters"] = [
        {"name": "site", "in": "query", "required": True}
    ]

    assert mon.compare_specs(old, new).breaking


@pytest.mark.parametrize("was_optional", [True, False])
def test_mandatory_request_body_is_a_bug(was_optional: bool) -> None:
    old, new = _base(), _base()
    get = old["paths"]["/v1/things"]["get"]
    body = {"content": {"application/json": {"schema": {"type": "object"}}}}
    if was_optional:
        get["requestBody"] = {**body, "required": False}
    new["paths"]["/v1/things"]["get"]["requestBody"] = {**body, "required": True}

    assert mon.compare_specs(old, new).breaking


def test_reusable_request_components_are_classified() -> None:
    old = _base()
    old["components"]["schemas"]["Shared"] = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }
    old["components"]["requestBodies"] = {
        "Body": {
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Shared"}}}
        }
    }
    old["components"]["parameters"] = {"site": {"name": "site", "in": "query"}}
    body_change, param_change = copy.deepcopy(old), copy.deepcopy(old)
    body_change["components"]["schemas"]["Shared"]["required"] = ["name"]
    param_change["components"]["parameters"]["site"]["required"] = True

    assert mon.compare_specs(old, body_change).breaking
    assert mon.compare_specs(old, param_change).breaking


def test_path_level_servers_are_compared() -> None:
    old, new = _base(), _base()
    new["paths"]["/v1/things"]["servers"] = [{"url": "https://example.invalid"}]

    assert not mon.compare_specs(old, new).is_empty


def test_updated_issue_keeps_every_tracked_version() -> None:
    body = _report("3.0.0").body(history=("2.0.0",))
    versions = [m.group("version") for m in mon.MARKER_RE.finditer(body)]
    issue = mon.TrackedIssue(1, "closed", "network", "3.0.0", (), tuple(versions))

    assert versions == ["2.0.0", "3.0.0"]
    assert mon.plan_action(_report("2.0.0"), [issue]).kind == "skip"
