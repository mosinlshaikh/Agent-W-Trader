"""SQLite-backed persistence for complete order snapshots."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from domain.models import Order


class SQLiteOrderRepository:
    """Durably stores typed orders without coupling domain code to an ORM."""

    def __init__(self, database_path: str = "data/agent_w_trader.db") -> None:
        self.database_path = database_path
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save(self, order: Order) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO orders (id, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (order.id, order.model_dump_json(), order.updated_at.isoformat()),
            )

    def get(self, order_id: str) -> Optional[Order]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
        return Order.model_validate_json(row["payload"]) if row else None

    def list_all(self) -> list[Order]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM orders ORDER BY updated_at ASC"
            ).fetchall()
        return [Order.model_validate_json(row["payload"]) for row in rows]
