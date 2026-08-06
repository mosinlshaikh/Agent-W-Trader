"""Append-only SQLite event store for authoritative portfolio accounting."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from portfolio.ledger_models import LedgerEvent


class DuplicateLedgerEventError(RuntimeError):
    """Raised when an event id or external financial reference is replayed."""


class LedgerIntegrityError(RuntimeError):
    """Raised when persisted financial history fails its integrity check."""


class SQLiteLedgerEventStore:
    """Durable append-only journal with duplicate-reference and tamper detection."""

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
                    reference_id TEXT,
                    occurred_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_hash TEXT NOT NULL
                )
                """
            )
            # Safe forward migration for databases created by the earlier milestone.
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(portfolio_events)").fetchall()
            }
            if "reference_id" not in columns:
                connection.execute("ALTER TABLE portfolio_events ADD COLUMN reference_id TEXT")
            if "payload_hash" not in columns:
                connection.execute("ALTER TABLE portfolio_events ADD COLUMN payload_hash TEXT")
                rows = connection.execute(
                    "SELECT sequence, payload FROM portfolio_events"
                ).fetchall()
                for row in rows:
                    connection.execute(
                        "UPDATE portfolio_events SET payload_hash = ? WHERE sequence = ?",
                        (self._hash(row["payload"]), row["sequence"]),
                    )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_portfolio_events_reference
                ON portfolio_events(reference_id)
                WHERE reference_id IS NOT NULL
                """
            )

    @staticmethod
    def _hash(payload: str) -> str:
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def append(self, event: LedgerEvent) -> int:
        payload = event.model_dump_json()
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO portfolio_events(
                        event_id, reference_id, occurred_at, payload, payload_hash
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.reference_id,
                        event.occurred_at.isoformat(),
                        payload,
                        self._hash(payload),
                    ),
                )
                return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            duplicate_key = event.reference_id or event.event_id
            raise DuplicateLedgerEventError(duplicate_key) from exc

    def read_all(self) -> list[LedgerEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT sequence, event_id, payload, payload_hash
                FROM portfolio_events
                ORDER BY sequence ASC
                """
            ).fetchall()

        events: list[LedgerEvent] = []
        for row in rows:
            expected = self._hash(row["payload"])
            if row["payload_hash"] != expected:
                raise LedgerIntegrityError(
                    f"portfolio event integrity failure at sequence {row['sequence']} "
                    f"({row['event_id']})"
                )
            events.append(LedgerEvent.model_validate_json(row["payload"]))
        return events

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM portfolio_events").fetchone()
        return int(row["total"])
