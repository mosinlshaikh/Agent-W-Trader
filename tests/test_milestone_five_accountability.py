from datetime import datetime, timedelta, timezone

import pytest

from risk.risk_engine import RiskEngine
from strategy.accountability import (
    DuplicateOutcomeError,
    QuarantinePolicy,
    SQLiteDecisionJournal,
    UnknownDecisionError,
    UnknownOrderAttributionError,
)
from strategy.decision_gate import (
    DecisionStatus,
    SignalAction,
    StrategyDecisionGate,
    StrategySignal,
)


def signal(*, strategy="MOMENTUM", symbol="TCS", price=100.0, confidence=0.90):
    return StrategySignal(
        strategy=strategy,
        symbol=symbol,
        action=SignalAction.BUY,
        confidence=confidence,
        quantity=1,
        reference_price=price,
        stop_loss_price=price - 5,
        generated_at=datetime.now(timezone.utc),
        rationale=["trend confirmed"],
    )


def make_gate(tmp_path, *, policy=None):
    journal = SQLiteDecisionJournal(
        tmp_path / "accountability.db",
        quarantine_policy=policy,
    )
    gate = StrategyDecisionGate(
        RiskEngine(account_equity=100_000),
        cooldown=timedelta(0),
        decision_journal=journal,
    )
    return gate, journal


def test_every_decision_is_persisted_and_counted(tmp_path):
    gate, journal = make_gate(tmp_path)
    approved = gate.evaluate(signal(price=100))
    rejected = gate.evaluate(signal(price=101, confidence=0.20))
    held = gate.evaluate(
        StrategySignal(
            strategy="MOMENTUM",
            symbol="TCS",
            action=SignalAction.HOLD,
            confidence=0.95,
            reference_price=102,
        )
    )

    assert approved.status == DecisionStatus.APPROVED
    assert rejected.status == DecisionStatus.REJECTED
    assert held.status == DecisionStatus.SUPPRESSED
    stats = journal.statistics("momentum")
    assert stats.total_decisions == 3
    assert stats.approved == 1
    assert stats.rejected == 1
    assert stats.suppressed == 1
    assert len(journal.recent_decisions()) == 3


def test_signal_decision_order_and_pnl_are_traceable(tmp_path):
    gate, journal = make_gate(tmp_path)
    decision = gate.evaluate(signal())
    journal.link_order(decision.decision_id, "paper-order-1")
    stats = journal.record_outcome("paper-order-1", 750.0)

    trace = journal.decision_for_order("paper-order-1")
    assert trace is not None
    assert trace["decision_id"] == decision.decision_id
    assert trace["signal_id"] == decision.signal_id
    assert trace["strategy"] == "MOMENTUM"
    assert trace["realized_pnl"] == pytest.approx(750)
    assert stats.closed_trades == 1
    assert stats.wins == 1
    assert stats.cumulative_pnl == pytest.approx(750)


def test_worker_history_survives_restart(tmp_path):
    path = tmp_path / "accountability.db"
    journal = SQLiteDecisionJournal(path)
    gate = StrategyDecisionGate(
        RiskEngine(account_equity=100_000),
        cooldown=timedelta(0),
        decision_journal=journal,
    )
    decision = gate.evaluate(signal(strategy="MEAN_REVERSION"))
    journal.link_order(decision.decision_id, "paper-order-restart")
    journal.record_outcome("paper-order-restart", -125.0)

    restarted = SQLiteDecisionJournal(path)
    stats = restarted.statistics("MEAN_REVERSION")
    assert stats.total_decisions == 1
    assert stats.closed_trades == 1
    assert stats.losses == 1
    assert stats.cumulative_pnl == pytest.approx(-125)


def test_poor_worker_is_automatically_quarantined(tmp_path):
    policy = QuarantinePolicy(
        min_closed_trades=3,
        max_loss_rate=0.66,
        max_cumulative_loss=-500,
        minimum_performance_score=35,
    )
    gate, journal = make_gate(tmp_path, policy=policy)

    for index, pnl in enumerate([-250.0, -200.0, -175.0]):
        decision = gate.evaluate(signal(price=100 + index))
        order_id = f"loss-order-{index}"
        journal.link_order(decision.decision_id, order_id)
        journal.record_outcome(order_id, pnl)

    stats = journal.statistics("MOMENTUM")
    assert stats.quarantined is True
    assert stats.quarantine_reason

    blocked = gate.evaluate(signal(price=110))
    assert blocked.status == DecisionStatus.SUPPRESSED
    assert blocked.reason_code == "WORKER_QUARANTINED"


def test_manual_reinstatement_requires_audit_note(tmp_path):
    policy = QuarantinePolicy(min_closed_trades=1, max_loss_rate=1.0, max_cumulative_loss=-1)
    gate, journal = make_gate(tmp_path, policy=policy)
    decision = gate.evaluate(signal())
    journal.link_order(decision.decision_id, "loss")
    journal.record_outcome("loss", -10)
    assert journal.is_quarantined("MOMENTUM")

    with pytest.raises(ValueError):
        journal.reinstate("MOMENTUM", note="")
    journal.reinstate("MOMENTUM", note="Reviewed by operator after strategy fix")
    assert journal.is_quarantined("MOMENTUM") is False


def test_attribution_errors_fail_closed(tmp_path):
    _, journal = make_gate(tmp_path)
    with pytest.raises(UnknownDecisionError):
        journal.link_order("missing-decision", "order-1")
    with pytest.raises(UnknownOrderAttributionError):
        journal.record_outcome("missing-order", 10)

    gate = StrategyDecisionGate(
        RiskEngine(account_equity=100_000),
        decision_journal=journal,
    )
    decision = gate.evaluate(signal())
    journal.link_order(decision.decision_id, "order-2")
    journal.record_outcome("order-2", 25)
    with pytest.raises(DuplicateOutcomeError):
        journal.record_outcome("order-2", 25)
