from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class EmailMessage:
    recipient: str
    subject: str
    body: str


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> Path | None: ...


class FileEmailSender:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def send(self, message: EmailMessage) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        safe_subject = message.subject.lower().replace(" ", "-")
        path = self.output_dir / f"{safe_subject}.txt"
        path.write_text(
            f"To: {message.recipient}\nSubject: {message.subject}\n\n{message.body}\n",
            encoding="utf-8",
        )
        return path
