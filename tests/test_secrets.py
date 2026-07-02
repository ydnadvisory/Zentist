from pathlib import Path

import pytest

from zentist_rpa.connectors.secrets import OrangeHRMSecrets
from zentist_rpa.core.exceptions import ConfigurationError


def test_orangehrm_secrets_load_configured_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZENTIST_RPA_REPORT_RECIPIENT", "ops@example.com")
    monkeypatch.setenv("ZENTIST_RPA_ORANGEHRM_USERNAME_SECRET", "Admin")
    monkeypatch.setenv("ZENTIST_RPA_ORANGEHRM_PASSWORD_SECRET", "password")

    secrets = OrangeHRMSecrets()

    assert secrets.get_secret("username") == "Admin"
    assert secrets.get_secret("password") == "password"


def test_orangehrm_secrets_fail_for_missing_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ZENTIST_RPA_REPORT_RECIPIENT", "ops@example.com")
    monkeypatch.delenv("ZENTIST_RPA_ORANGEHRM_USERNAME_SECRET", raising=False)

    secrets = OrangeHRMSecrets()

    with pytest.raises(ConfigurationError, match="username"):
        secrets.get_secret("username")
