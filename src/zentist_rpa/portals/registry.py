from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import argparse

    from zentist_rpa.connectors.settings import RuntimeSettings
    from zentist_rpa.core.models import RunContext, WorkItemOutcome

PortalParserConfigurator = Callable[["argparse.ArgumentParser"], None]
PortalContextBuilder = Callable[["argparse.Namespace"], "RunContext"]
PortalSettingsValidator = Callable[["RuntimeSettings"], None]
PortalRunnerCallable = Callable[
    ["argparse.Namespace", "RunContext", "RuntimeSettings"],
    Coroutine[Any, Any, list["WorkItemOutcome"]],
]


@dataclass(frozen=True)
class PortalAdapter:
    name: str
    configure_parser: PortalParserConfigurator
    validate_settings: PortalSettingsValidator
    build_context: PortalContextBuilder
    run: PortalRunnerCallable


_PORTAL_REGISTRY: dict[str, PortalAdapter] = {}


def register_portal(adapter: PortalAdapter) -> None:
    if adapter.name in _PORTAL_REGISTRY:
        msg = f"Portal '{adapter.name}' is already registered"
        raise ValueError(msg)
    _PORTAL_REGISTRY[adapter.name] = adapter


def get_portal(name: str) -> PortalAdapter:
    return _PORTAL_REGISTRY[name]


def get_portal_names() -> tuple[str, ...]:
    return tuple(sorted(_PORTAL_REGISTRY))
