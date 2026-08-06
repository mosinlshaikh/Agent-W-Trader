"""Mark-to-market portfolio valuation with fail-closed price safety."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from portfolio.ledger_models import PortfolioState


class MissingPriceError(RuntimeError):
    pass


class StalePriceError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReferencePrice:
    symbol: str
    price: float
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError("reference price must be positive")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        object.__setattr__(self, "symbol", self.symbol.strip().upper())


@dataclass(frozen=True)
class PositionValuation:
    symbol: str
    quantity: int
    average_price: float
    market_price: float
    market_value: float
    unrealized_pnl: float


@dataclass(frozen=True)
class PortfolioValuation:
    valued_at: datetime
    cash_balance: float
    gross_market_value: float
    unrealized_pnl: float
    realized_pnl: float
    net_liquidation_value: float
    positions: tuple[PositionValuation, ...]


class MarkToMarketEngine:
    def __init__(self, max_price_age: timedelta = timedelta(seconds=15)) -> None:
        if max_price_age <= timedelta(0):
            raise ValueError("max_price_age must be positive")
        self.max_price_age = max_price_age

    def value(
        self,
        state: PortfolioState,
        prices: dict[str, ReferencePrice],
        *,
        valued_at: datetime | None = None,
    ) -> PortfolioValuation:
        now = valued_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("valued_at must be timezone-aware")

        valued_positions: list[PositionValuation] = []
        gross_market_value = 0.0
        unrealized_pnl = 0.0

        normalized = {symbol.strip().upper(): price for symbol, price in prices.items()}
        for symbol, position in sorted(state.positions.items()):
            quote = normalized.get(symbol)
            if quote is None:
                raise MissingPriceError(symbol)
            if now - quote.observed_at > self.max_price_age:
                raise StalePriceError(symbol)
            market_value = position.quantity * quote.price
            position_unrealized = (quote.price - position.average_price) * position.quantity
            gross_market_value += abs(market_value)
            unrealized_pnl += position_unrealized
            valued_positions.append(
                PositionValuation(
                    symbol=symbol,
                    quantity=position.quantity,
                    average_price=position.average_price,
                    market_price=quote.price,
                    market_value=market_value,
                    unrealized_pnl=position_unrealized,
                )
            )

        return PortfolioValuation(
            valued_at=now,
            cash_balance=state.cash_balance,
            gross_market_value=gross_market_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=state.realized_pnl,
            net_liquidation_value=state.cash_balance + sum(p.market_value for p in valued_positions),
            positions=tuple(valued_positions),
        )


class SQLiteValuationSnapshotStore:
    """Persists immutable valuation snapshots for restart-safe audit and recovery."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS valuation_snapshots (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    valued_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def append(self, valuation: PortfolioValuation) -> int:
        payload = {
            "valued_at": valuation.valued_at.isoformat(),
            "cash_balance": valuation.cash_balance,
            "gross_market_value": valuation.gross_market_value,
            "unrealized_pnl": valuation.unrealized_pnl,
            "realized_pnl": valuation.realized_pnl,
            "net_liquidation_value": valuation.net_liquidation_value,
            "positions": [position.__dict__ for position in valuation.positions],
        }
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO valuation_snapshots(valued_at, payload) VALUES (?, ?)",
                (valuation.valued_at.isoformat(), json.dumps(payload, sort_keys=True)),
            )
            return int(cursor.lastrowid)

    def latest(self) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM valuation_snapshots ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        return None if row is None else json.loads(row["payload"])
