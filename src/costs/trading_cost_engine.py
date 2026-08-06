"""Effective-dated trading-cost and true net-P&L accounting.

Rates are configuration data, not legal constants. The engine fails closed when
no schedule is valid for the trade date, preventing gross P&L from being
mistaken for realizable net performance.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path


class InstrumentSegment(str, Enum):
    EQUITY_INTRADAY = "EQUITY_INTRADAY"
    EQUITY_DELIVERY = "EQUITY_DELIVERY"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class MissingFeeScheduleError(RuntimeError):
    pass


class OverlappingFeeScheduleError(RuntimeError):
    pass


@dataclass(frozen=True)
class FeeSchedule:
    schedule_id: str
    segment: InstrumentSegment
    effective_from: date
    effective_to: date | None = None
    brokerage_rate: float = 0.0
    brokerage_cap: float | None = None
    stt_buy_rate: float = 0.0
    stt_sell_rate: float = 0.0
    exchange_rate: float = 0.0
    sebi_rate: float = 0.0
    gst_rate: float = 0.0
    stamp_buy_rate: float = 0.0
    stamp_sell_rate: float = 0.0
    slippage_bps: float = 0.0

    def __post_init__(self) -> None:
        if not self.schedule_id.strip():
            raise ValueError("schedule_id cannot be blank")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")
        rates = (
            self.brokerage_rate,
            self.stt_buy_rate,
            self.stt_sell_rate,
            self.exchange_rate,
            self.sebi_rate,
            self.gst_rate,
            self.stamp_buy_rate,
            self.stamp_sell_rate,
            self.slippage_bps,
        )
        if any(rate < 0 for rate in rates):
            raise ValueError("fee and slippage rates cannot be negative")
        if self.brokerage_cap is not None and self.brokerage_cap < 0:
            raise ValueError("brokerage_cap cannot be negative")


@dataclass(frozen=True)
class TradeCostInput:
    trade_id: str
    segment: InstrumentSegment
    side: TradeSide
    quantity: int
    execution_price: float
    reference_price: float
    traded_at: datetime
    gross_pnl: float

    def __post_init__(self) -> None:
        if not self.trade_id.strip():
            raise ValueError("trade_id cannot be blank")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.execution_price <= 0 or self.reference_price <= 0:
            raise ValueError("prices must be positive")
        if self.traded_at.tzinfo is None:
            raise ValueError("traded_at must be timezone-aware")


@dataclass(frozen=True)
class TradingCostBreakdown:
    schedule_id: str
    turnover: float
    brokerage: float
    stt: float
    exchange_charges: float
    sebi_charges: float
    gst: float
    stamp_duty: float
    modeled_slippage: float
    observed_slippage: float
    total_costs: float
    gross_pnl: float
    net_pnl: float


class SQLiteFeeScheduleStore:
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
                CREATE TABLE IF NOT EXISTS fee_schedules (
                    schedule_id TEXT PRIMARY KEY,
                    segment TEXT NOT NULL,
                    effective_from TEXT NOT NULL,
                    effective_to TEXT,
                    brokerage_rate REAL NOT NULL,
                    brokerage_cap REAL,
                    stt_buy_rate REAL NOT NULL,
                    stt_sell_rate REAL NOT NULL,
                    exchange_rate REAL NOT NULL,
                    sebi_rate REAL NOT NULL,
                    gst_rate REAL NOT NULL,
                    stamp_buy_rate REAL NOT NULL,
                    stamp_sell_rate REAL NOT NULL,
                    slippage_bps REAL NOT NULL
                )
                """
            )

    def add(self, schedule: FeeSchedule) -> None:
        if self._overlaps(schedule):
            raise OverlappingFeeScheduleError(schedule.schedule_id)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO fee_schedules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    schedule.schedule_id,
                    schedule.segment.value,
                    schedule.effective_from.isoformat(),
                    schedule.effective_to.isoformat() if schedule.effective_to else None,
                    schedule.brokerage_rate,
                    schedule.brokerage_cap,
                    schedule.stt_buy_rate,
                    schedule.stt_sell_rate,
                    schedule.exchange_rate,
                    schedule.sebi_rate,
                    schedule.gst_rate,
                    schedule.stamp_buy_rate,
                    schedule.stamp_sell_rate,
                    schedule.slippage_bps,
                ),
            )

    def resolve(self, segment: InstrumentSegment, on_date: date) -> FeeSchedule:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM fee_schedules
                WHERE segment = ?
                  AND effective_from <= ?
                  AND (effective_to IS NULL OR effective_to >= ?)
                ORDER BY effective_from DESC
                LIMIT 1
                """,
                (segment.value, on_date.isoformat(), on_date.isoformat()),
            ).fetchone()
        if row is None:
            raise MissingFeeScheduleError(f"{segment.value} on {on_date.isoformat()}")
        return self._from_row(row)

    def _overlaps(self, candidate: FeeSchedule) -> bool:
        candidate_end = candidate.effective_to or date.max
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT effective_from, effective_to FROM fee_schedules WHERE segment = ?",
                (candidate.segment.value,),
            ).fetchall()
        for row in rows:
            existing_start = date.fromisoformat(row["effective_from"])
            existing_end = date.fromisoformat(row["effective_to"]) if row["effective_to"] else date.max
            if candidate.effective_from <= existing_end and existing_start <= candidate_end:
                return True
        return False

    @staticmethod
    def _from_row(row: sqlite3.Row) -> FeeSchedule:
        return FeeSchedule(
            schedule_id=row["schedule_id"],
            segment=InstrumentSegment(row["segment"]),
            effective_from=date.fromisoformat(row["effective_from"]),
            effective_to=date.fromisoformat(row["effective_to"]) if row["effective_to"] else None,
            brokerage_rate=row["brokerage_rate"],
            brokerage_cap=row["brokerage_cap"],
            stt_buy_rate=row["stt_buy_rate"],
            stt_sell_rate=row["stt_sell_rate"],
            exchange_rate=row["exchange_rate"],
            sebi_rate=row["sebi_rate"],
            gst_rate=row["gst_rate"],
            stamp_buy_rate=row["stamp_buy_rate"],
            stamp_sell_rate=row["stamp_sell_rate"],
            slippage_bps=row["slippage_bps"],
        )


class TradingCostEngine:
    def __init__(self, schedules: SQLiteFeeScheduleStore) -> None:
        self.schedules = schedules

    def calculate(self, trade: TradeCostInput) -> TradingCostBreakdown:
        schedule = self.schedules.resolve(trade.segment, trade.traded_at.date())
        turnover = trade.quantity * trade.execution_price
        brokerage = turnover * schedule.brokerage_rate
        if schedule.brokerage_cap is not None:
            brokerage = min(brokerage, schedule.brokerage_cap)

        stt_rate = schedule.stt_buy_rate if trade.side == TradeSide.BUY else schedule.stt_sell_rate
        stamp_rate = schedule.stamp_buy_rate if trade.side == TradeSide.BUY else schedule.stamp_sell_rate
        stt = turnover * stt_rate
        exchange = turnover * schedule.exchange_rate
        sebi = turnover * schedule.sebi_rate
        stamp = turnover * stamp_rate
        gst = (brokerage + exchange + sebi) * schedule.gst_rate
        modeled_slippage = turnover * schedule.slippage_bps / 10_000
        observed_slippage = abs(trade.execution_price - trade.reference_price) * trade.quantity
        slippage = max(modeled_slippage, observed_slippage)
        total = brokerage + stt + exchange + sebi + gst + stamp + slippage
        return TradingCostBreakdown(
            schedule_id=schedule.schedule_id,
            turnover=turnover,
            brokerage=brokerage,
            stt=stt,
            exchange_charges=exchange,
            sebi_charges=sebi,
            gst=gst,
            stamp_duty=stamp,
            modeled_slippage=modeled_slippage,
            observed_slippage=observed_slippage,
            total_costs=total,
            gross_pnl=trade.gross_pnl,
            net_pnl=trade.gross_pnl - total,
        )
