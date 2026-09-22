from datetime import datetime, timezone

import pytest

from portfolio.ledger_models import PortfolioState, PositionState
from portfolio.portfolio_reconciler import (
    BrokerPortfolioSnapshot,
    PortfolioReconciler,
    PortfolioTradingGate,
    ReconciliationAuditStore,
    ReconciliationSeverity,
    TradingFrozenError,
)


def make_reconciler(tmp_path):
    gate = PortfolioTradingGate()
    store = ReconciliationAuditStore(tmp_path / "reconciliation.db")
    return PortfolioReconciler(store, gate), store, gate


def test_matching_portfolio_keeps_trading_open(tmp_path):
    reconciler, store, gate = make_reconciler(tmp_path)
    internal = PortfolioState(
        cash_balance=50_000,
        positions={"RELIANCE": PositionState(symbol="RELIANCE", quantity=10, average_price=2500)},
    )
    broker = BrokerPortfolioSnapshot(
        cash_balance=50_000,
        positions={"reliance": 10},
        captured_at=datetime.now(timezone.utc),
        net_liquidation_value=76_000,
    )

    report = reconciler.reconcile(
        internal,
        broker,
        internal_net_liquidation_value=76_000,
    )

    assert report.severity == ReconciliationSeverity.MATCH
    assert report.trading_frozen is False
    assert report.mismatches == ()
    gate.assert_trading_allowed()
    assert store.latest() == report


def test_small_cash_difference_is_warning_without_freeze(tmp_path):
    reconciler, _, gate = make_reconciler(tmp_path)
    internal = PortfolioState(cash_balance=50_000)
    broker = BrokerPortfolioSnapshot(
        cash_balance=50_010,
        positions={},
        captured_at=datetime.now(timezone.utc),
    )

    report = reconciler.reconcile(internal, broker)

    assert report.severity == ReconciliationSeverity.WARNING
    assert report.trading_frozen is False
    assert report.mismatches[0].field == "cash_balance"
    gate.assert_trading_allowed()


def test_position_difference_is_critical_and_freezes_trading(tmp_path):
    reconciler, _, gate = make_reconciler(tmp_path)
    internal = PortfolioState(
        cash_balance=10_000,
        positions={"INFY": PositionState(symbol="INFY", quantity=5, average_price=1500)},
    )
    broker = BrokerPortfolioSnapshot(
        cash_balance=10_000,
        positions={"INFY": 4},
        captured_at=datetime.now(timezone.utc),
    )

    report = reconciler.reconcile(internal, broker)

    assert report.severity == ReconciliationSeverity.CRITICAL
    assert report.trading_frozen is True
    assert report.mismatches[0].symbol == "INFY"
    with pytest.raises(TradingFrozenError):
        gate.assert_trading_allowed()


def test_large_cash_or_nlv_difference_is_critical(tmp_path):
    reconciler, _, gate = make_reconciler(tmp_path)
    internal = PortfolioState(cash_balance=100_000)
    broker = BrokerPortfolioSnapshot(
        cash_balance=99_000,
        positions={},
        captured_at=datetime.now(timezone.utc),
        net_liquidation_value=98_000,
    )

    report = reconciler.reconcile(
        internal,
        broker,
        internal_net_liquidation_value=100_000,
    )

    assert report.severity == ReconciliationSeverity.CRITICAL
    assert {item.field for item in report.mismatches} == {
        "cash_balance",
        "net_liquidation_value",
    }
    assert gate.frozen is True


def test_clean_reconciliation_can_release_previous_freeze(tmp_path):
    reconciler, _, gate = make_reconciler(tmp_path)
    internal = PortfolioState(cash_balance=25_000)
    bad = BrokerPortfolioSnapshot(
        cash_balance=20_000,
        positions={},
        captured_at=datetime.now(timezone.utc),
    )
    reconciler.reconcile(internal, bad)
    assert gate.frozen is True

    clean = BrokerPortfolioSnapshot(
        cash_balance=25_000,
        positions={},
        captured_at=datetime.now(timezone.utc),
    )
    report = reconciler.reconcile(internal, clean)

    assert report.severity == ReconciliationSeverity.MATCH
    assert gate.frozen is False
    gate.assert_trading_allowed()


def test_audit_record_survives_restart(tmp_path):
    path = tmp_path / "reconciliation.db"
    gate = PortfolioTradingGate()
    reconciler = PortfolioReconciler(ReconciliationAuditStore(path), gate)
    report = reconciler.reconcile(
        PortfolioState(cash_balance=10_000),
        BrokerPortfolioSnapshot(
            cash_balance=9_500,
            positions={},
            captured_at=datetime.now(timezone.utc),
        ),
    )

    restarted_store = ReconciliationAuditStore(path)
    restored = restarted_store.latest()
    assert restored is not None
    assert restored.reconciliation_id == report.reconciliation_id
    assert restored.severity == ReconciliationSeverity.CRITICAL
    assert restored.trading_frozen is True
