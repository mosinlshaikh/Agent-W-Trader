from datetime import datetime, timedelta, timezone

from risk.risk_engine import RiskEngine, RiskLimits
from strategy.decision_gate import (
    DecisionStatus,
    SignalAction,
    StrategyDecisionGate,
    StrategySignal,
)


NOW = datetime(2026, 8, 4, 3, 0, tzinfo=timezone.utc)


def make_gate(**kwargs) -> StrategyDecisionGate:
    return StrategyDecisionGate(
        RiskEngine(
            account_equity=1_000_000,
            limits=RiskLimits(
                max_trade_risk_percent=1,
                max_daily_loss_percent=2,
                max_order_value=500_000,
            ),
        ),
        **kwargs,
    )


def make_signal(**overrides) -> StrategySignal:
    values = {
        "strategy": "momentum",
        "symbol": "reliance",
        "action": SignalAction.BUY,
        "confidence": 0.82,
        "quantity": 10,
        "reference_price": 2_500,
        "stop_loss_price": 2_450,
        "generated_at": NOW - timedelta(seconds=10),
        "rationale": ["breakout", "volume confirmation"],
    }
    values.update(overrides)
    return StrategySignal(**values)


def test_approved_signal_contains_order_and_risk_evidence():
    result = make_gate().evaluate(make_signal(), now=NOW)
    assert result.status == DecisionStatus.APPROVED
    assert result.reason_code == "ALL_CHECKS_PASSED"
    assert result.order_request is not None
    assert result.order_request.symbol == "RELIANCE"
    assert result.risk_decision is not None
    assert result.risk_decision.approved is True


def test_low_confidence_is_rejected():
    result = make_gate(minimum_confidence=0.70).evaluate(
        make_signal(confidence=0.69), now=NOW
    )
    assert result.status == DecisionStatus.REJECTED
    assert result.reason_code == "LOW_CONFIDENCE"


def test_duplicate_semantic_signal_is_suppressed():
    gate = make_gate()
    first = make_signal(signal_id="signal-1")
    duplicate = make_signal(signal_id="signal-2")
    assert gate.evaluate(first, now=NOW).status == DecisionStatus.APPROVED
    result = gate.evaluate(duplicate, now=NOW + timedelta(seconds=1))
    assert result.status == DecisionStatus.SUPPRESSED
    assert result.reason_code == "DUPLICATE_SIGNAL"


def test_cooldown_blocks_changed_repeat_signal():
    gate = make_gate(cooldown=timedelta(minutes=5))
    first = make_signal(signal_id="signal-1")
    changed = make_signal(signal_id="signal-2", reference_price=2_501)
    assert gate.evaluate(first, now=NOW).status == DecisionStatus.APPROVED
    result = gate.evaluate(changed, now=NOW + timedelta(minutes=1))
    assert result.status == DecisionStatus.SUPPRESSED
    assert result.reason_code == "COOLDOWN_ACTIVE"


def test_existing_long_position_suppresses_new_buy():
    result = make_gate().evaluate(
        make_signal(), existing_position_quantity=10, now=NOW
    )
    assert result.status == DecisionStatus.SUPPRESSED
    assert result.reason_code == "POSITION_ALREADY_OPEN"


def test_sell_without_position_is_suppressed():
    result = make_gate().evaluate(
        make_signal(
            action=SignalAction.SELL,
            stop_loss_price=2_550,
        ),
        existing_position_quantity=0,
        now=NOW,
    )
    assert result.status == DecisionStatus.SUPPRESSED
    assert result.reason_code == "NO_POSITION_TO_EXIT"


def test_stale_signal_is_rejected():
    result = make_gate(maximum_signal_age=timedelta(minutes=2)).evaluate(
        make_signal(generated_at=NOW - timedelta(minutes=3)), now=NOW
    )
    assert result.status == DecisionStatus.REJECTED
    assert result.reason_code == "STALE_SIGNAL"


def test_risk_engine_rejection_is_propagated_with_evidence():
    result = make_gate().evaluate(
        make_signal(quantity=300, reference_price=2_500, stop_loss_price=2_450),
        now=NOW,
    )
    assert result.status == DecisionStatus.REJECTED
    assert result.reason_code == "RISK_REJECTED"
    assert result.risk_decision is not None
    assert result.risk_decision.approved is False


def test_equal_strategy_disagreement_rejects_entire_batch():
    gate = make_gate(minimum_consensus_ratio=0.60)
    results = gate.evaluate_consensus(
        [
            make_signal(strategy="momentum", action=SignalAction.BUY),
            make_signal(
                strategy="mean-reversion",
                action=SignalAction.SELL,
                stop_loss_price=2_550,
            ),
        ],
        existing_position_quantity=10,
        now=NOW,
    )
    assert all(result.status == DecisionStatus.REJECTED for result in results)
    assert all(result.reason_code == "STRATEGY_DISAGREEMENT" for result in results)


def test_majority_consensus_suppresses_minority_direction():
    gate = make_gate(minimum_consensus_ratio=0.60)
    results = gate.evaluate_consensus(
        [
            make_signal(strategy="momentum", signal_id="one"),
            make_signal(strategy="breakout", signal_id="two", reference_price=2_501),
            make_signal(
                strategy="mean-reversion",
                signal_id="three",
                action=SignalAction.SELL,
                stop_loss_price=2_550,
            ),
        ],
        now=NOW,
    )
    assert sum(result.status == DecisionStatus.APPROVED for result in results) == 2
    minority = [result for result in results if result.reason_code == "MINORITY_DIRECTION"]
    assert len(minority) == 1
