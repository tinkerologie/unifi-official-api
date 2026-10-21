"""Every public signature in the package can be introspected at runtime."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Callable, Iterator
from types import ModuleType
from unittest.mock import create_autospec

import pytest

import unifi_official_api


def _modules() -> Iterator[ModuleType]:
    yield unifi_official_api
    for info in pkgutil.walk_packages(
        unifi_official_api.__path__, f"{unifi_official_api.__name__}."
    ):
        yield importlib.import_module(info.name)


def _callables() -> Iterator[tuple[str, Callable[..., object]]]:
    for module in _modules():
        for name, obj in vars(module).items():
            if getattr(obj, "__module__", None) != module.__name__:
                continue
            if inspect.isfunction(obj):
                yield f"{module.__name__}.{name}", obj
            elif inspect.isclass(obj):
                for attr, member in vars(obj).items():
                    if inspect.isfunction(member):
                        yield f"{module.__name__}.{name}.{attr}", member
                    elif isinstance(member, property) and member.fget is not None:
                        yield f"{module.__name__}.{name}.{attr}", member.fget


CALLABLES = dict(_callables())


def test_the_package_has_callables_to_check() -> None:
    """The scan finds the package's functions and methods."""
    assert len(CALLABLES) > 100


@pytest.mark.parametrize("name", sorted(CALLABLES))
def test_signature_is_introspectable(name: str) -> None:
    """``inspect.signature`` works, so mocks and tooling can read it.

    A module without ``from __future__ import annotations`` evaluates its
    annotations when they are read; a type imported only under
    ``TYPE_CHECKING`` then raises ``NameError``.
    """
    inspect.signature(CALLABLES[name])


def test_clients_can_be_autospecced() -> None:
    """``create_autospec`` works on every public client class."""
    clients = [
        obj
        for name, obj in vars(unifi_official_api).items()
        if inspect.isclass(obj) and name.endswith("Client")
    ]
    assert clients
    for client in clients:
        create_autospec(client, instance=True)
