from __future__ import annotations

# ruff: noqa: SLF001
import pytest

from zentist_rpa.portals import registry


def test_register_portal_rejects_duplicate_names(monkeypatch: pytest.MonkeyPatch) -> None:
    original = dict(registry._PORTAL_REGISTRY)
    monkeypatch.setattr(registry, "_PORTAL_REGISTRY", {})

    async def run(
        _args: object,
        _context: object,
        _settings: object,
    ) -> list[object]:
        return []

    adapter = registry.PortalAdapter(
        name="orangehrm",
        configure_parser=lambda parser: None,  # noqa: ARG005
        validate_settings=lambda settings: None,  # noqa: ARG005
        build_context=lambda args: None,  # noqa: ARG005
        run=run,
    )

    registry.register_portal(adapter)
    with pytest.raises(ValueError, match="already registered"):
        registry.register_portal(adapter)

    registry._PORTAL_REGISTRY.clear()
    registry._PORTAL_REGISTRY.update(original)
