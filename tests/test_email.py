from pathlib import Path

from zentist_rpa.connectors.email import EmailMessage, FileEmailSender


def test_file_email_sender_writes_message(tmp_path: Path) -> None:
    sender = FileEmailSender(tmp_path)

    path = sender.send(
        EmailMessage(
            recipient="ops@example.com",
            subject="Daily RPA Report",
            body="No secrets here.",
        ),
    )

    assert path == tmp_path / "daily-rpa-report.txt"
    assert path.read_text(encoding="utf-8") == (
        "To: ops@example.com\nSubject: Daily RPA Report\n\nNo secrets here.\n"
    )
