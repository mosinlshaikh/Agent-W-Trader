"""Safety-focused tests for the operational paper-trading core."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from domain.models import OrderRequest, OrderSide, OrderStatus
from execution.order_manager import InvalidOrderTransitionError, OrderManager
from risk.risk_engine import RiskEngine, RiskLimits


def build_request(**overrides):
    values = {
        "symbol": "RELIANCE",
        "side": OrderSide.BUY,
        "quantity": 10,
        "reference_price": 100.0,
        "stop_loss_price": 95.0,
    }
    values.update(overrides)
    return OrderRequest(**values)


def test_invalid_quantity_is_rejected():
    with pytest.raises(ValidationError):
        build_request(quantity=0)


def test_valid_order_is_approved_when_risk_is_within_limit():
    manager = OrderManager(RiskEngine(account_equity=100_000))

    order = manager.create_order(build_request())

    assert order.status == OrderStatus.APPROVED
    assert order.risk_decision is not None
    assert order.risk_decision.approved is True
    assert order.risk_decision.estimated_risk_amount == 50.0


def test_trade_is_rejected_when_risk_exceeds_account_limit():
    manager = OrderManager(
        RiskEngine(
            account_equity=10_000,
            limits=RiskLimits(max_trade_risk_percent=1.0),
        )
    )

    order = manager.create_order(
        build_request(quantity=100, reference_price=100, stop_loss_price=90)
    )

    assert order.status == OrderStatus.RISK_REJECTED
    assert order.risk_decision is not None
    assert order.risk_decision.approved is False


def test_daily_loss_limit_blocks_new_orders():
    engine = RiskEngine(account_equity=100_000)
    engine.set_realized_pnl_today(-2_000)
    manager = OrderManager(engine)

    order = manager.create_order(build_request())

    assert order.status == OrderStatus.RISK_REJECTED
    assert "daily loss" in order.risk_decision.reason.lower()


def test_kill_switch_blocks_new_orders():
    engine = RiskEngine(account_equity=100_000)
    engine.activate_kill_switch()
    manager = OrderManager(engine)

    order = manager.create_order(build_request())

    assert order.status == OrderStatus.RISK_REJECTED
    assert "kill switch" in order.risk_decision.reason.lower()


def test_safe_order_lifecycle():
    manager = OrderManager(RiskEngine(account_equity=100_000))
    order = manager.create_order(build_request())

    assert manager.mark_submitted(order.id).status == OrderStatus.SUBMITTED
    assert manager.mark_filled(order.id).status == OrderStatus.FILLED

    with pytest.raises(InvalidOrderTransitionError):
        manager.cancel(order.id)
