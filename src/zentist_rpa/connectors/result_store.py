from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from zentist_rpa.core.models import OutcomeStatus, RunContext, RunStatus, WorkItemOutcome

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


class ResultStore(Protocol):
    def start_run(self, context: RunContext) -> None: ...

    def record_outcomes(self, run_id: str, outcomes: Sequence[WorkItemOutcome]) -> None: ...

    def finish_run(self, run_id: str, status: RunStatus) -> None: ...


class SQLiteResultStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS work_item_outcomes (
                    run_id TEXT NOT NULL,
                    portal TEXT NOT NULL,
                    item_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT,
                    attempts INTEGER NOT NULL,
                    output_refs_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, portal, item_key),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                """,
            )

    def start_run(self, context: RunContext) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (run_id, started_at, status)
                VALUES (?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    started_at = excluded.started_at,
                    status = excluded.status
                """,
                (context.run_id, context.started_at.isoformat(), RunStatus.STARTED.value),
            )

    def record_outcomes(self, run_id: str, outcomes: Sequence[WorkItemOutcome]) -> None:
        self.initialize()
        now = datetime.now(tz=UTC).isoformat()
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO work_item_outcomes (
                    run_id,
                    portal,
                    item_key,
                    status,
                    reason,
                    attempts,
                    output_refs_json,
                    recorded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, portal, item_key) DO UPDATE SET
                    status = excluded.status,
                    reason = excluded.reason,
                    attempts = excluded.attempts,
                    output_refs_json = excluded.output_refs_json,
                    recorded_at = excluded.recorded_at
                """,
                [
                    (
                        run_id,
                        outcome.portal,
                        outcome.item_key,
                        outcome.status.value,
                        outcome.reason,
                        outcome.attempts,
                        json.dumps(dict(outcome.output_refs), sort_keys=True),
                        now,
                    )
                    for outcome in outcomes
                ],
            )

    def finish_run(self, run_id: str, status: RunStatus) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE runs
                SET status = ?, finished_at = ?
                WHERE run_id = ?
                """,
                (status.value, datetime.now(tz=UTC).isoformat(), run_id),
            )

    def fetch_outcomes(self, run_id: str) -> list[WorkItemOutcome]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT portal, item_key, status, reason, attempts, output_refs_json
                FROM work_item_outcomes
                WHERE run_id = ?
                ORDER BY portal, item_key
                """,
                (run_id,),
            ).fetchall()

        return [
            WorkItemOutcome(
                portal=row["portal"],
                item_key=row["item_key"],
                status=OutcomeStatus(row["status"]),
                reason=row["reason"],
                attempts=row["attempts"],
                output_refs=json.loads(row["output_refs_json"]),
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection
