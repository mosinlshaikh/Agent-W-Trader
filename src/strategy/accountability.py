"""Persistent strategy-worker accountability, outcome attribution, and quarantine."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from strategy.decision_gate import DecisionEvidence, StrategySignal


class AccountabilityError(RuntimeError):
    """Base error for accountability journal failures."""


class UnknownDecisionError(AccountabilityError):
    pass


class UnknownOrderAttributionError(AccountabilityError):
    pass


class DuplicateOutcomeError(AccountabilityError):
    pass


@dataclass(frozen=True)
class QuarantinePolicy:
    min_closed_trades: int = 5
    max_loss_rate: float = 0.65
    max_cumulative_loss: float = -1_000.0
    minimum_performance_score: float = 35.0

    def __post_init__(self) -> None:
        if self.min_closed_trades <= 0:
            raise ValueError("min_closed_trades must be positive")
        if not 0 <= self.max_loss_rate <= 1:
            raise ValueError("max_loss_rate must be between 0 and 1")
        if not 0 <= self.minimum_performance_score <= 100:
            raise ValueError("minimum_performance_score must be between 0 and 100")


@dataclass(frozen=True)
class WorkerStatistics:
    strategy: str
    total_decisions: int
    approved: int
    rejected: int
    suppressed: int
    closed_trades: int
    wins: int
    losses: int
    cumulative_pnl: float
    average_pnl: float
    win_rate: float
    performance_score: float
    quarantined: bool
    quarantine_reason: str | None


class SQLiteDecisionJournal:
    """Restart-safe decision ledger with order and realized-P&L attribution."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        quarantine_policy: QuarantinePolicy | None = None,
    ) -> None:
        self.database_path = str(database_path)
        self.quarantine_policy = quarantine_policy or QuarantinePolicy()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS worker_decisions (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id TEXT NOT NULL UNIQUE,
                    signal_id TEXT NOT NULL UNIQUE,
                    strategy TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    fingerprint TEXT NOT NULL,
                    evaluated_at TEXT NOT NULL,
                    order_id TEXT UNIQUE,
                    realized_pnl REAL,
                    outcome_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_worker_decisions_strategy
                    ON worker_decisions(strategy, sequence);
                CREATE INDEX IF NOT EXISTS idx_worker_decisions_order
                    ON worker_decisions(order_id);
                CREATE TABLE IF NOT EXISTS worker_quarantine (
                    strategy TEXT PRIMARY KEY,
                    quarantined INTEGER NOT NULL DEFAULT 0,
                    reason TEXT,
                    changed_at TEXT NOT NULL,
                    reinstatement_note TEXT
                );
                """
            )

    def record_decision(
        self,
        signal: "StrategySignal",
        evidence: "DecisionEvidence",
        *,
        order_id: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO worker_decisions(
                    decision_id, signal_id, strategy, symbol, status,
                    reason_code, explanation, confidence, fingerprint,
                    evaluated_at, order_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.decision_id,
                    signal.signal_id,
                    signal.strategy,
                    signal.symbol,
                    evidence.status.value,
                    evidence.reason_code,
                    evidence.explanation,
                    evidence.confidence,
                    evidence.fingerprint,
                    evidence.evaluated_at.isoformat(),
                    order_id,
                ),
            )

    def link_order(self, decision_id: str, order_id: str) -> None:
        if not order_id.strip():
            raise ValueError("order_id cannot be blank")
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE worker_decisions SET order_id = ? WHERE decision_id = ?",
                (order_id.strip(), decision_id),
            )
            if cursor.rowcount != 1:
                raise UnknownDecisionError(decision_id)

    def record_outcome(
        self,
        order_id: str,
        realized_pnl: float,
        *,
        occurred_at: datetime | None = None,
    ) -> WorkerStatistics:
        timestamp = occurred_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT strategy, realized_pnl FROM worker_decisions WHERE order_id = ?",
                (order_id,),
            ).fetchone()
            if row is None:
                raise UnknownOrderAttributionError(order_id)
            if row["realized_pnl"] is not None:
                raise DuplicateOutcomeError(order_id)
            connection.execute(
                """
                UPDATE worker_decisions
                SET realized_pnl = ?, outcome_at = ?
                WHERE order_id = ?
                """,
                (float(realized_pnl), timestamp.isoformat(), order_id),
            )
            strategy = str(row["strategy"])
        statistics = self.statistics(strategy)
        self._apply_quarantine_policy(statistics)
        return self.statistics(strategy)

    def is_quarantined(self, strategy: str) -> bool:
        normalized = strategy.strip().upper()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT quarantined FROM worker_quarantine WHERE strategy = ?",
                (normalized,),
            ).fetchone()
        return bool(row and row["quarantined"])

    def quarantine_reason(self, strategy: str) -> str | None:
        normalized = strategy.strip().upper()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT reason FROM worker_quarantine WHERE strategy = ? AND quarantined = 1",
                (normalized,),
            ).fetchone()
        return None if row is None else str(row["reason"])

    def reinstate(self, strategy: str, *, note: str) -> None:
        if not note.strip():
            raise ValueError("reinstatement note is required")
        normalized = strategy.strip().upper()
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO worker_quarantine(strategy, quarantined, reason, changed_at, reinstatement_note)
                VALUES (?, 0, NULL, ?, ?)
                ON CONFLICT(strategy) DO UPDATE SET
                    quarantined = 0,
                    reason = NULL,
                    changed_at = excluded.changed_at,
                    reinstatement_note = excluded.reinstatement_note
                """,
                (normalized, now, note.strip()),
            )

    def statistics(self, strategy: str) -> WorkerStatistics:
        normalized = strategy.strip().upper()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_decisions,
                    SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) AS approved,
                    SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected,
                    SUM(CASE WHEN status = 'SUPPRESSED' THEN 1 ELSE 0 END) AS suppressed,
                    SUM(CASE WHEN realized_pnl IS NOT NULL THEN 1 ELSE 0 END) AS closed_trades,
                    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) AS losses,
                    COALESCE(SUM(realized_pnl), 0) AS cumulative_pnl,
                    COALESCE(AVG(realized_pnl), 0) AS average_pnl
                FROM worker_decisions
                WHERE strategy = ?
                """,
                (normalized,),
            ).fetchone()
            quarantine = connection.execute(
                "SELECT quarantined, reason FROM worker_quarantine WHERE strategy = ?",
                (normalized,),
            ).fetchone()

        total = int(row["total_decisions"] or 0)
        approved = int(row["approved"] or 0)
        rejected = int(row["rejected"] or 0)
        suppressed = int(row["suppressed"] or 0)
        closed = int(row["closed_trades"] or 0)
        wins = int(row["wins"] or 0)
        losses = int(row["losses"] or 0)
        cumulative = float(row["cumulative_pnl"] or 0.0)
        average = float(row["average_pnl"] or 0.0)
        win_rate = wins / closed if closed else 0.0
        decision_quality = approved / total if total else 0.0
        profitability = max(-20.0, min(20.0, average / 50.0))
        score = max(0.0, min(100.0, 40.0 + win_rate * 40.0 + decision_quality * 20.0 + profitability))
        return WorkerStatistics(
            strategy=normalized,
            total_decisions=total,
            approved=approved,
            rejected=rejected,
            suppressed=suppressed,
            closed_trades=closed,
            wins=wins,
            losses=losses,
            cumulative_pnl=cumulative,
            average_pnl=average,
            win_rate=win_rate,
            performance_score=score,
            quarantined=bool(quarantine and quarantine["quarantined"]),
            quarantine_reason=None if quarantine is None else quarantine["reason"],
        )

    def decision_for_order(self, order_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM worker_decisions WHERE order_id = ?",
                (order_id,),
            ).fetchone()
        return None if row is None else dict(row)

    def recent_decisions(self, *, limit: int = 100) -> list[dict[str, object]]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM worker_decisions ORDER BY sequence DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _apply_quarantine_policy(self, statistics: WorkerStatistics) -> None:
        policy = self.quarantine_policy
        if statistics.closed_trades < policy.min_closed_trades:
            return
        loss_rate = statistics.losses / statistics.closed_trades
        reasons: list[str] = []
        if loss_rate >= policy.max_loss_rate:
            reasons.append(f"loss rate {loss_rate:.0%} exceeded {policy.max_loss_rate:.0%}")
        if statistics.cumulative_pnl <= policy.max_cumulative_loss:
            reasons.append(
                f"cumulative P&L {statistics.cumulative_pnl:.2f} breached {policy.max_cumulative_loss:.2f}"
            )
        if statistics.performance_score < policy.minimum_performance_score:
            reasons.append(
                f"performance score {statistics.performance_score:.1f} below {policy.minimum_performance_score:.1f}"
            )
        if not reasons:
            return
        now = datetime.now(timezone.utc).isoformat()
        reason = "; ".join(reasons)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO worker_quarantine(strategy, quarantined, reason, changed_at, reinstatement_note)
                VALUES (?, 1, ?, ?, NULL)
                ON CONFLICT(strategy) DO UPDATE SET
                    quarantined = 1,
                    reason = excluded.reason,
                    changed_at = excluded.changed_at,
                    reinstatement_note = NULL
                """,
                (statistics.strategy, reason, now),
            )
