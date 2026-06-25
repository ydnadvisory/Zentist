from typing import Protocol


class SecretProvider(Protocol):
    def get_secret(self, name: str) -> str: ...
