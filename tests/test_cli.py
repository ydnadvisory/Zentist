import pytest

from zentist_rpa.cli import main


def test_check_config_validates_environment(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ZENTIST_RPA_REPORT_RECIPIENT", "ops@example.com")

    assert main(["check-config"]) == 0

    assert "Configuration valid" in capsys.readouterr().out


def test_structure_command_prints_boundaries(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["structure"]) == 0

    output = capsys.readouterr().out
    assert "core: runner contracts" in output
    assert "portals/orangehrm" in output
    assert "portals/saucedemo" in output
