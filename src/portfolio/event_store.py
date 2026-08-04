"""Append-only SQLite event store for authoritative portfolio accounting."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from portfolio.ledger_models import LedgerEvent


class DuplicateLedgerEventError(RuntimeError):
    pass


class SQLiteLedgerEventStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    occurred_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def append(self, event: LedgerEvent) -> int:
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO portfolio_events(event_id, occurred_at, payload) VALUES (?, ?, ?)",
                    (event.event_id, event.occurred_at.isoformat(), event.model_dump_json()),
                )
                return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise DuplicateLedgerEventError(event.event_id) from exc

    def read_all(self) -> list[LedgerEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM portfolio_events ORDER BY sequence ASC"
            ).fetchall()
        return [LedgerEvent.model_validate_json(row["payload"]) for row in rows]

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM portfolio_events").fetchone()
        return int(row["total"])
