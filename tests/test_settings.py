import pytest
from pydantic import ValidationError

from zentist_rpa.connectors.settings import RuntimeSettings


def test_runtime_settings_require_report_recipient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ZENTIST_RPA_REPORT_RECIPIENT", raising=False)

    with pytest.raises(ValidationError, match="ZENTIST_RPA_REPORT_RECIPIENT"):
        RuntimeSettings(_env_file=None)


def test_runtime_settings_load_report_recipient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZENTIST_RPA_REPORT_RECIPIENT", "ops@example.com")

    settings = RuntimeSettings()

    assert settings.report_recipient == "ops@example.com"
