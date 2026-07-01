from typing import Protocol

from zentist_rpa.connectors.settings import RuntimeSettings
from zentist_rpa.core.exceptions import ConfigurationError


class SecretProvider(Protocol):
    def get_secret(self, name: str) -> str: ...


class OrangeHRMSecrets:
    def __init__(self) -> None:
        settings = RuntimeSettings()
        self._secret_store = {
            "username": settings.orangehrm_username_secret,
            "password": settings.orangehrm_password_secret,
        }

    def get_secret(self, name: str) -> str:
        value = self._secret_store.get(name)
        if not value:
            msg = f"OrangeHRM secret '{name}' is not configured"
            raise ConfigurationError(msg)
        return value
