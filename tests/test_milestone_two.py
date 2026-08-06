from datetime import datetime, timedelta, timezone

import pytest

from domain.models import OrderRequest, OrderSide, OrderStatus
from execution.order_manager import OrderManager
from execution.paper_broker import PaperBroker
from market.data_guard import MarketDataGuard, MarketSnapshot, StaleMarketDataError
from persistence.order_repository import SQLiteOrderRepository
from risk.risk_engine import RiskEngine


def request() -> OrderRequest:
    return OrderRequest(
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10,
        reference_price=100.0,
        stop_loss_price=95.0,
    )


def test_order_survives_manager_restart(tmp_path):
    repository = SQLiteOrderRepository(str(tmp_path / "orders.db"))
    first = OrderManager(RiskEngine(100_000), repository)
    created = first.create_order(request())
    second = OrderManager(RiskEngine(100_000), repository)
    assert second.get_order(created.id).status == OrderStatus.APPROVED


def test_fresh_snapshot_executes_and_persists_fill(tmp_path):
    repository = SQLiteOrderRepository(str(tmp_path / "orders.db"))
    manager = OrderManager(RiskEngine(100_000), repository)
    order = manager.create_order(request())
    broker = PaperBroker(MarketDataGuard(max_age_seconds=5), slippage_bps=2)
    snapshot = MarketSnapshot(
        symbol="RELIANCE", price=100.0, observed_at=datetime.now(timezone.utc)
    )
    filled = manager.execute_paper(order.id, broker, snapshot)
    restored = repository.get(order.id)
    assert filled.status == OrderStatus.FILLED
    assert filled.fill_price == 100.02
    assert restored is not None
    assert restored.broker_order_id.startswith("PAPER-")


def test_stale_snapshot_fails_closed_and_marks_rejected(tmp_path):
    repository = SQLiteOrderRepository(str(tmp_path / "orders.db"))
    manager = OrderManager(RiskEngine(100_000), repository)
    order = manager.create_order(request())
    broker = PaperBroker(MarketDataGuard(max_age_seconds=2))
    snapshot = MarketSnapshot(
        symbol="RELIANCE",
        price=100.0,
        observed_at=datetime.now(timezone.utc) - timedelta(seconds=10),
    )
    with pytest.raises(StaleMarketDataError):
        manager.execute_paper(order.id, broker, snapshot)
    assert repository.get(order.id).status == OrderStatus.REJECTED


def test_snapshot_symbol_mismatch_is_blocked(tmp_path):
    manager = OrderManager(RiskEngine(100_000))
    order = manager.create_order(request())
    broker = PaperBroker(MarketDataGuard())
    snapshot = MarketSnapshot(
        symbol="TCS", price=100.0, observed_at=datetime.now(timezone.utc)
    )
    with pytest.raises(ValueError, match="symbol"):
        manager.execute_paper(order.id, broker, snapshot)
