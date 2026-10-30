"""The API update monitor reports real spec changes only, and never the same version twice."""

from __future__ import annotations

import copy
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
