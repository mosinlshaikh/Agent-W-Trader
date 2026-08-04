from datetime import date, datetime, timedelta, timezone
from io import StringIO
import json
import logging

import pytest

from domain.models import Order, OrderRequest, OrderSide, OrderStatus
from execution.idempotency import DuplicateOrderError, IdempotencyGuard
from execution.reconciler import BrokerOrderState, OrderReconciler
from market.adapter import InMemoryMarketDataAdapter
from market.session_calendar import MarketSessionCalendar
from observability.health import ComponentHealth, HealthService, HealthStatus
from observability.structured_logging import JsonFormatter


def request() -> OrderRequest:
    return OrderRequest(
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10,
        reference_price=100.0,
        stop_loss_price=95.0,
    )


def test_market_adapter_requires_connection_and_normalizes_symbol():
    adapter = InMemoryMarketDataAdapter()
    with pytest.raises(RuntimeError):
        adapter.publish("reliance", 100.0)
    adapter.connect()
    adapter.publish("reliance", 100.0)
    snapshot = adapter.get_snapshot("RELIANCE")
    assert snapshot.symbol == "RELIANCE"
    assert snapshot.price == 100.0


def test_market_session_blocks_weekends_and_holidays():
    holiday = date(2026, 8, 5)
    calendar = MarketSessionCalendar(holidays={holiday})
    weekday_open = datetime(2026, 8, 4, 10, 0, tzinfo=calendar.timezone)
    holiday_open = datetime(2026, 8, 5, 10, 0, tzinfo=calendar.timezone)
    weekend = datetime(2026, 8, 8, 10, 0, tzinfo=calendar.timezone)
    assert calendar.is_open(weekday_open)
    assert not calendar.is_open(holiday_open)
    assert not calendar.is_open(weekend)


def test_idempotency_guard_blocks_duplicate_inside_window():
    guard = IdempotencyGuard(window_seconds=30)
    now = datetime.now(timezone.utc)
    guard.register(request(), now=now)
    with pytest.raises(DuplicateOrderError):
        guard.register(request(), now=now + timedelta(seconds=5))
    guard.register(request(), now=now + timedelta(seconds=31))


def test_reconciler_updates_forward_state_and_ignores_regression():
    order = Order(request=request(), status=OrderStatus.SUBMITTED)
    order.broker_order_id = "PAPER-1"
    reconciler = OrderReconciler()
    result = reconciler.reconcile(
        [order],
        {"PAPER-1": BrokerOrderState("PAPER-1", OrderStatus.FILLED, 100.2)},
    )[0]
    assert result.changed
    assert order.status == OrderStatus.FILLED
    assert order.fill_price == 100.2

    regression = reconciler.reconcile(
        [order],
        {"PAPER-1": BrokerOrderState("PAPER-1", OrderStatus.SUBMITTED)},
    )[0]
    assert not regression.changed
    assert order.status == OrderStatus.FILLED


def test_health_service_aggregates_failure_without_crashing():
    service = HealthService()
    service.register(
        "database",
        lambda: ComponentHealth("database", HealthStatus.HEALTHY, "ready"),
    )
    service.register("broker", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    health = service.evaluate()
    assert health.status == HealthStatus.UNHEALTHY
    assert len(health.components) == 2


def test_json_formatter_emits_machine_readable_record():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("milestone-three-test")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.info("order accepted", extra={"event": "ORDER_ACCEPTED", "order_id": "123"})
    payload = json.loads(stream.getvalue())
    assert payload["event"] == "ORDER_ACCEPTED"
    assert payload["order_id"] == "123"
