"""Portfolio reconciliation, audit trail, and fail-closed trading gate."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from portfolio.ledger_models import PortfolioState


class ReconciliationSeverity(str, Enum):
    MATCH = "MATCH"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class BrokerPortfolioSnapshot:
    cash_balance: float
    positions: dict[str, int]
    captured_at: datetime
    net_liquidation_value: float | None = None


@dataclass(frozen=True)
class PortfolioMismatch:
    field: str
    symbol: str | None
    internal_value: float
    broker_value: float
    difference: float
    severity: ReconciliationSeverity


@dataclass(frozen=True)
class PortfolioReconciliationReport:
    reconciliation_id: str
    reconciled_at: datetime
    severity: ReconciliationSeverity
    trading_frozen: bool
    mismatches: tuple[PortfolioMismatch, ...]


class TradingFrozenError(RuntimeError):
    pass


class ReconciliationAuditStore:
    """Persists immutable reconciliation evidence for restart-safe review."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio_reconciliations (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    reconciliation_id TEXT NOT NULL UNIQUE,
                    reconciled_at TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    trading_frozen INTEGER NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def append(self, report: PortfolioReconciliationReport) -> None:
        payload = {
            "reconciliation_id": report.reconciliation_id,
            "reconciled_at": report.reconciled_at.isoformat(),
            "severity": report.severity.value,
            "trading_frozen": report.trading_frozen,
            "mismatches": [
                {**asdict(item), "severity": item.severity.value}
                for item in report.mismatches
            ],
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO portfolio_reconciliations(
                    reconciliation_id, reconciled_at, severity, trading_frozen, payload
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    report.reconciliation_id,
                    report.reconciled_at.isoformat(),
                    report.severity.value,
                    int(report.trading_frozen),
                    json.dumps(payload, sort_keys=True),
                ),
            )

    def latest(self) -> PortfolioReconciliationReport | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM portfolio_reconciliations ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload"])
        return PortfolioReconciliationReport(
            reconciliation_id=payload["reconciliation_id"],
            reconciled_at=datetime.fromisoformat(payload["reconciled_at"]),
            severity=ReconciliationSeverity(payload["severity"]),
            trading_frozen=bool(payload["trading_frozen"]),
            mismatches=tuple(
                PortfolioMismatch(
                    field=item["field"],
                    symbol=item["symbol"],
                    internal_value=float(item["internal_value"]),
                    broker_value=float(item["broker_value"]),
                    difference=float(item["difference"]),
                    severity=ReconciliationSeverity(item["severity"]),
                )
                for item in payload["mismatches"]
            ),
        )


class PortfolioTradingGate:
    """Fail-closed gate controlled exclusively by reconciliation evidence."""

    def __init__(self) -> None:
        self._frozen = False
        self._reason = ""

    @property
    def frozen(self) -> bool:
        return self._frozen

    @property
    def reason(self) -> str:
        return self._reason

    def apply(self, report: PortfolioReconciliationReport) -> None:
        self._frozen = report.trading_frozen
        self._reason = (
            f"portfolio reconciliation {report.reconciliation_id} is critical"
            if report.trading_frozen
            else ""
        )

    def assert_trading_allowed(self) -> None:
        if self._frozen:
            raise TradingFrozenError(self._reason)


class PortfolioReconciler:
    """Compares broker truth with the internal event-sourced portfolio state."""

    def __init__(
        self,
        audit_store: ReconciliationAuditStore,
        gate: PortfolioTradingGate,
        *,
        cash_warning_tolerance: float = 1.0,
        cash_critical_tolerance: float = 100.0,
        nlv_warning_tolerance: float = 5.0,
        nlv_critical_tolerance: float = 500.0,
    ) -> None:
        self.audit_store = audit_store
        self.gate = gate
        self.cash_warning_tolerance = cash_warning_tolerance
        self.cash_critical_tolerance = cash_critical_tolerance
        self.nlv_warning_tolerance = nlv_warning_tolerance
        self.nlv_critical_tolerance = nlv_critical_tolerance

    @staticmethod
    def _severity(difference: float, warning: float, critical: float) -> ReconciliationSeverity:
        magnitude = abs(difference)
        if magnitude > critical:
            return ReconciliationSeverity.CRITICAL
        if magnitude > warning:
            return ReconciliationSeverity.WARNING
        return ReconciliationSeverity.MATCH

    def reconcile(
        self,
        internal: PortfolioState,
        broker: BrokerPortfolioSnapshot,
        *,
        internal_net_liquidation_value: float | None = None,
        now: datetime | None = None,
    ) -> PortfolioReconciliationReport:
        mismatches: list[PortfolioMismatch] = []
        cash_difference = broker.cash_balance - internal.cash_balance
        cash_severity = self._severity(
            cash_difference,
            self.cash_warning_tolerance,
            self.cash_critical_tolerance,
        )
        if cash_severity != ReconciliationSeverity.MATCH:
            mismatches.append(
                PortfolioMismatch(
                    field="cash_balance",
                    symbol=None,
                    internal_value=internal.cash_balance,
                    broker_value=broker.cash_balance,
                    difference=cash_difference,
                    severity=cash_severity,
                )
            )

        internal_positions = {symbol.upper(): item.quantity for symbol, item in internal.positions.items()}
        broker_positions = {symbol.strip().upper(): int(quantity) for symbol, quantity in broker.positions.items()}
        for symbol in sorted(set(internal_positions) | set(broker_positions)):
            local_quantity = internal_positions.get(symbol, 0)
            broker_quantity = broker_positions.get(symbol, 0)
            difference = broker_quantity - local_quantity
            if difference:
                mismatches.append(
                    PortfolioMismatch(
                        field="position_quantity",
                        symbol=symbol,
                        internal_value=float(local_quantity),
                        broker_value=float(broker_quantity),
                        difference=float(difference),
                        severity=ReconciliationSeverity.CRITICAL,
                    )
                )

        if internal_net_liquidation_value is not None and broker.net_liquidation_value is not None:
            difference = broker.net_liquidation_value - internal_net_liquidation_value
            severity = self._severity(
                difference,
                self.nlv_warning_tolerance,
                self.nlv_critical_tolerance,
            )
            if severity != ReconciliationSeverity.MATCH:
                mismatches.append(
                    PortfolioMismatch(
                        field="net_liquidation_value",
                        symbol=None,
                        internal_value=internal_net_liquidation_value,
                        broker_value=broker.net_liquidation_value,
                        difference=difference,
                        severity=severity,
                    )
                )

        overall = ReconciliationSeverity.MATCH
        if any(item.severity == ReconciliationSeverity.CRITICAL for item in mismatches):
            overall = ReconciliationSeverity.CRITICAL
        elif mismatches:
            overall = ReconciliationSeverity.WARNING

        report = PortfolioReconciliationReport(
            reconciliation_id=str(uuid4()),
            reconciled_at=now or datetime.now(timezone.utc),
            severity=overall,
            trading_frozen=overall == ReconciliationSeverity.CRITICAL,
            mismatches=tuple(mismatches),
        )
        self.audit_store.append(report)
        self.gate.apply(report)
        return report
