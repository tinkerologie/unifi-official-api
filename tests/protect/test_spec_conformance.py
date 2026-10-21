"""
Guard: every request the Protect package sends is an operation in the pinned spec.

The spec is vendored unmodified at ``tests/fixtures/protect_openapi_<version>.json``,
downloaded from ``https://developer.ui.com/protect/v<version>/openapi.json`` where
``<version>`` is ``PROTECT_SPEC_VERSION``, so the guard runs offline. To move to a
new spec version, download the new document, delete the old one, and bump
``PROTECT_SPEC_VERSION`` in the same change.

Every public coroutine and async context manager on the client, and on each
endpoint the client exposes, is called against a recording transport. The
transport records the HTTP method and path of each request, then stops the call.
Every recorded operation must exist in the spec, every method must send at least
one request, and every ``build_api_path`` call site in the package must be
reached, so a new method or call site cannot slip past the guard.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import sys
from collections.abc import Callable, Iterator
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any, NamedTuple

import pytest

import unifi_official_api.protect as protect_pkg
from unifi_official_api import ApiKeyAuth, ConnectionType, LocalAuth, UniFiUnsupportedError
from unifi_official_api.const import PROTECT_SPEC_VERSION
from unifi_official_api.protect import UniFiProtectClient
from unifi_official_api.protect.models import RecordingMode

SPEC_PATH = (
    Path(__file__).parent.parent / "fixtures" / f"protect_openapi_{PROTECT_SPEC_VERSION}.json"
)
PACKAGE_DIR = Path(protect_pkg.__file__).parent
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete"})

# Arguments for required parameters, keyed by parameter name. Any other required
# parameter gets an ID such as ``id-camera-id``, which can never equal a literal
# path segment such as ``settings`` or ``enable``.
ARGUMENTS: dict[str, Any] = {
    "callback": lambda _message: None,
    "enabled": True,
    "led_level": 3,
    "mode": "auto",
    "preset_id": "1",
    "repeat_times": 1,
    "sensitivity": 50,
    "slot": 1,
    "transaction": {"type": "sale", "externalId": "id-transaction", "amount": 1.0},
    "volume": 50,
}
# Per-method arguments where the generic ones would fail validation first.
OVERRIDES: dict[str, dict[str, Any]] = {
    "application.upload_file": {"file_data": b"GIF89a", "filename": "a.gif"},
    "cameras.set_recording_mode": {"mode": RecordingMode.ALWAYS},
    "cameras.set_video_mode": {"mode": "default"},
    "lights.set_mode": {"mode": "always"},
    "websocket.subscribe_with_callback": {"subscription_type": "events", "reconnect": False},
}
# Responses for methods that read before they write; the write is what matters.
_CHIME = {
    "id": "id-chime-id",
    "mac": "AABBCCDDEEFF",
    "ringSettings": [{"cameraId": "id-cam", "repeatTimes": 1, "ringtoneId": "id-r", "volume": 50}],
}
STAGED_RESPONSES: dict[str, list[Any]] = {
    "chimes.set_repeat_times": [_CHIME],
    "chimes.set_ringtone": [_CHIME],
    "chimes.set_volume": [_CHIME],
}
# Public coroutines that never send a request.
NO_REQUEST = frozenset({"client.close"})
# Public coroutines that report an unsupported feature without a request.
UNSUPPORTED = frozenset({"chimes.play"})


class _RequestSentError(Exception):
    """Raised by the recording transport to stop a call once it has sent a request."""


class Operation(NamedTuple):
    """An HTTP operation, with its path in the spec's ``/v1/...`` form."""

    method: str
    path: str


def _load_spec() -> dict[str, Any]:
    spec: dict[str, Any] = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    return spec


def _spec_operations() -> list[tuple[re.Pattern[str], str, frozenset[str]]]:
    operations = []
    for template, item in _load_spec()["paths"].items():
        pattern = re.compile("^" + re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(template)) + "$")
        operations.append((pattern, template, frozenset(k for k in item if k in HTTP_METHODS)))
    return operations


SPEC_OPERATIONS = _spec_operations()


def _spec_template(operation: Operation) -> str | None:
    """
    Return the spec path template documenting ``operation``, or None.

    A path matching several templates belongs to the one with the fewest
    parameters, so ``/arm-profiles/enable`` is never read as ``/arm-profiles/{id}``.
    """
    matches = [
        (template.count("{"), template, methods)
        for pattern, template, methods in SPEC_OPERATIONS
        if pattern.match(operation.path)
    ]
    if not matches:
        return None
    _parameters, template, methods = min(matches)
    return template if operation.method in methods else None


class Recorder:
    """Recording transport installed on a client."""

    def __init__(self, client: UniFiProtectClient) -> None:
        self.operations: list[Operation] = []
        self.call_sites: set[tuple[str, str]] = set()
        self.staged: list[Any] = []
        self._prefix = client.build_api_path("/")
        build = client.build_api_path

        def build_api_path(endpoint: str, site_id: str | None = None) -> str:
            code = sys._getframe(1).f_code
            module = Path(code.co_filename).relative_to(PACKAGE_DIR).as_posix()
            self.call_sites.add((module, code.co_qualname))
            return build(endpoint, site_id)

        async def request(method: str, path: str, **_kwargs: Any) -> Any:
            return self._record(method, path)

        async def get_binary(path: str, **_kwargs: Any) -> Any:
            return self._record("GET", path)

        async def connect(path: str) -> Any:
            return self._record("GET", path)

        client.build_api_path = build_api_path  # type: ignore[method-assign]
        client._request = request  # type: ignore[method-assign]
        client._get_binary_with_content_type = get_binary  # type: ignore[method-assign]
        client.websocket._connect = connect  # type: ignore[method-assign]

    def _record(self, method: str, path: str) -> Any:
        assert path.startswith(self._prefix), path
        self.operations.append(Operation(method.lower(), "/v1/" + path.removeprefix(self._prefix)))
        if self.staged:
            return self.staged.pop(0)
        raise _RequestSentError


def _make_client(connection_type: ConnectionType) -> UniFiProtectClient:
    if connection_type == ConnectionType.LOCAL:
        return UniFiProtectClient(auth=LocalAuth(api_key="key"), base_url="https://console")
    return UniFiProtectClient(
        auth=ApiKeyAuth(api_key="key"),
        connection_type=ConnectionType.REMOTE,
        console_id="id-console",
    )


def _public_targets(client: UniFiProtectClient) -> Iterator[tuple[str, Callable[..., Any]]]:
    """Yield every public coroutine or async context manager on the client surface."""
    owners: list[tuple[str, object]] = [("client", client)]
    for name, attr in inspect.getmembers(type(client)):
        if isinstance(attr, property) and not name.startswith("_"):
            owners.append((name, getattr(client, name)))
    for owner_name, owner in owners:
        for name, member in inspect.getmembers(owner, inspect.ismethod):
            function = inspect.unwrap(member)
            if not name.startswith("_") and (
                inspect.iscoroutinefunction(function) or inspect.isasyncgenfunction(function)
            ):
                yield f"{owner_name}.{name}", member


def _arguments(target: str, function: Callable[..., Any]) -> tuple[list[Any], dict[str, Any]]:
    args: list[Any] = []
    kwargs: dict[str, Any] = {}
    overrides = OVERRIDES.get(target, {})
    for parameter in inspect.signature(function).parameters.values():
        if parameter.kind is parameter.VAR_KEYWORD:
            kwargs["name"] = "renamed"
            continue
        if parameter.name in overrides:
            value = overrides[parameter.name]
        elif parameter.default is not parameter.empty:
            continue
        else:
            value = ARGUMENTS.get(parameter.name, f"id-{parameter.name.replace('_', '-')}")
        if parameter.kind is parameter.KEYWORD_ONLY:
            kwargs[parameter.name] = value
        else:
            args.append(value)
    return args, kwargs


async def _invoke(target: Callable[..., Any], args: list[Any], kwargs: dict[str, Any]) -> None:
    result = target(*args, **kwargs)
    if isinstance(result, AbstractAsyncContextManager):
        async with result:
            pass
    else:
        await result


async def _exercise(client: UniFiProtectClient) -> tuple[Recorder, dict[str, list[Operation]]]:
    """Call every public target once and return what each one sent."""
    recorder = Recorder(client)
    sent: dict[str, list[Operation]] = {}
    for name, target in _public_targets(client):
        if name in NO_REQUEST | UNSUPPORTED:
            continue
        before = len(recorder.operations)
        recorder.staged = list(STAGED_RESPONSES.get(name, []))
        with pytest.raises(_RequestSentError):
            await _invoke(target, *_arguments(name, target))
        sent[name] = recorder.operations[before:]
    return recorder, sent


def _ast_call_sites() -> set[tuple[str, str]]:
    """Return (module, qualified function) for every build_api_path call in the package."""
    sites: set[tuple[str, str]] = set()

    def visit(node: ast.AST, module: str, scope: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                visit(child, module, (*scope, child.name))
                continue
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == "build_api_path"
            ):
                sites.add((module, ".".join(scope)))
            visit(child, module, scope)

    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        visit(tree, path.relative_to(PACKAGE_DIR).as_posix(), ())
    return sites


def test_vendored_spec_is_the_pinned_version() -> None:
    """The vendored spec file matches PROTECT_SPEC_VERSION and has operations."""
    assert SPEC_PATH.is_file(), f"Vendor the Protect {PROTECT_SPEC_VERSION} spec at {SPEC_PATH}"
    assert len(SPEC_OPERATIONS) > 1


@pytest.mark.parametrize("connection_type", [ConnectionType.LOCAL, ConnectionType.REMOTE])
async def test_every_protect_request_is_in_the_spec(connection_type: ConnectionType) -> None:
    """Every public Protect method sends only operations the pinned spec documents."""
    _recorder, sent = await _exercise(_make_client(connection_type))

    off_spec = {
        name: [f"{op.method.upper()} {op.path}" for op in ops if _spec_template(op) is None]
        for name, ops in sent.items()
    }
    assert {name: ops for name, ops in off_spec.items() if ops} == {}
    assert len(sent) > 50


async def test_guard_reaches_every_build_api_path_call_site() -> None:
    """The exercise run reaches every build_api_path call site in the package."""
    recorder, _sent = await _exercise(_make_client(ConnectionType.LOCAL))

    assert recorder.call_sites == _ast_call_sites()


async def test_multi_request_methods_send_their_write() -> None:
    """Methods that read before writing are recorded through to the write."""
    _recorder, sent = await _exercise(_make_client(ConnectionType.LOCAL))

    assert sent["chimes.set_volume"] == [
        Operation("get", "/v1/chimes/id-chime-id"),
        Operation("patch", "/v1/chimes/id-chime-id"),
    ]


@pytest.mark.parametrize("name", sorted(UNSUPPORTED))
async def test_unsupported_methods_send_nothing(name: str) -> None:
    """Methods for features the spec lacks raise before sending a request."""
    client = _make_client(ConnectionType.LOCAL)
    recorder = Recorder(client)
    target = dict(_public_targets(client))[name]

    with pytest.raises(UniFiUnsupportedError):
        await _invoke(target, *_arguments(name, target))
    assert recorder.operations == []


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        (Operation("get", "/v1/nvrs"), "/v1/nvrs"),
        (Operation("get", "/v1/cameras/id-camera/snapshot"), "/v1/cameras/{id}/snapshot"),
        (Operation("post", "/v1/arm-profiles/enable"), "/v1/arm-profiles/enable"),
        (Operation("patch", "/v1/arm-profiles/enable"), None),
        (Operation("delete", "/v1/arm-profiles/settings"), None),
        (Operation("delete", "/v1/arm-profiles/id-profile"), "/v1/arm-profiles/{id}"),
        (Operation("post", "/v1/cameras/id-camera/restart"), None),
        (Operation("patch", "/v1/nvrs"), None),
        (Operation("get", "/v1/cameras/id-camera/snapshot/extra"), None),
    ],
)
def test_spec_matcher(operation: Operation, expected: str | None) -> None:
    """The matcher accepts documented operations and rejects undocumented ones."""
    assert _spec_template(operation) == expected
