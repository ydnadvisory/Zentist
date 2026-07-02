from __future__ import annotations

import runpy

import pytest


def test_main_module_invokes_cli_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[object | None] = [None]

    def fake_main() -> int:
        called[0] = 0
        return 0

    monkeypatch.setattr("zentist_rpa.cli.main", fake_main)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("zentist_rpa.__main__", run_name="zentist_rpa.__main__")

    assert exc.value.code == 0
    assert called[0] == 0
