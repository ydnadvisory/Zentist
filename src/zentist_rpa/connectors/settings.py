from __future__ import annotations

from pathlib import Path
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ZENTIST_RPA_",
        extra="ignore",
    )

    report_recipient: str | None = Field(default=None, min_length=3)
    database_path: Path = Path("var/zentist-rpa.sqlite3")
    report_output_dir: Path = Path("var/reports")
    email_output_dir: Path = Path("var/email")
    orangehrm_username_secret: str | None = Field(default=None, min_length=3)
    orangehrm_password_secret: str | None = Field(default=None, min_length=3)

    @model_validator(mode="after")
    def require_report_recipient(self) -> Self:
        if self.report_recipient is None:
            msg = "ZENTIST_RPA_REPORT_RECIPIENT is required"
            raise ValueError(msg)
        return self
