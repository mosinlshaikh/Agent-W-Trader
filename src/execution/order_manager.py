"""Risk-gated, persistent order lifecycle for safe paper trading."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from domain.models import Order, OrderRequest, OrderStatus
from execution.idempotency import IdempotencyGuard
from execution.paper_broker import PaperBroker
from market.data_guard import MarketSnapshot
from market.session_calendar import MarketSessionCalendar
from observability.structured_logging import configure_logging
from persistence.order_repository import SQLiteOrderRepository
from risk.risk_engine import RiskEngine


class OrderNotFoundError(KeyError):
    """Raised when an order identifier cannot be resolved."""


class InvalidOrderTransitionError(RuntimeError):
    """Raised when an unsafe order-state transition is requested."""


class OrderManager:
    """Creates, risk-checks, persists, and paper-executes orders."""

    def __init__(
        self,
        risk_engine: RiskEngine,
        repository: Optional[SQLiteOrderRepository] = None,
        idempotency_guard: Optional[IdempotencyGuard] = None,
        session_calendar: Optional[MarketSessionCalendar] = None,
    ) -> None:
        self.risk_engine = risk_engine
        self.repository = repository
        self.idempotency_guard = idempotency_guard
        self.session_calendar = session_calendar
        self.logger = configure_logging()
        self._orders: Dict[str, Order] = {}
        if repository:
            self._orders = {order.id: order for order in repository.list_all()}

    def _save(self, order: Order) -> Order:
        order.updated_at = datetime.now(timezone.utc)
        self._orders[order.id] = order
        if self.repository:
            self.repository.save(order)
        return order

    def create_order(self, request: OrderRequest) -> Order:
        if self.idempotency_guard:
            self.idempotency_guard.register(request)
        order = Order(request=request)
        decision = self.risk_engine.evaluate(request)
        order.risk_decision = decision
        order.status = (
            OrderStatus.APPROVED if decision.approved else OrderStatus.RISK_REJECTED
        )
        self._save(order)
        self.logger.info(
            "order evaluated",
            extra={
                "event": "ORDER_EVALUATED",
                "order_id": order.id,
                "symbol": request.symbol,
            },
        )
        return order

    def get_order(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None and self.repository:
            order = self.repository.get(order_id)
            if order:
                self._orders[order.id] = order
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

    def list_orders(self) -> list[Order]:
        return list(self._orders.values())

    def execute_paper(
        self, order_id: str, broker: PaperBroker, snapshot: MarketSnapshot
    ) -> Order:
        order = self.get_order(order_id)
        if order.status != OrderStatus.APPROVED:
            raise InvalidOrderTransitionError(
                f"Only APPROVED orders can be executed; current={order.status}"
            )
        if self.session_calendar:
            self.session_calendar.assert_open(snapshot.timestamp)
        order.status = OrderStatus.SUBMITTED
        self._save(order)
        try:
            fill = broker.execute(order.model_copy(update={"status": OrderStatus.APPROVED}), snapshot)
        except Exception:
            order.status = OrderStatus.REJECTED
            self._save(order)
            self.logger.exception(
                "paper execution rejected",
                extra={"event": "ORDER_REJECTED", "order_id": order.id, "symbol": order.request.symbol},
            )
            raise
        order.broker_order_id = fill.broker_order_id
        order.fill_price = fill.fill_price
        order.status = OrderStatus.FILLED
        self._save(order)
        self.logger.info(
            "paper order filled",
            extra={
                "event": "ORDER_FILLED",
                "order_id": order.id,
                "symbol": order.request.symbol,
                "broker_order_id": order.broker_order_id,
            },
        )
        return order

    def mark_submitted(self, order_id: str) -> Order:
        order = self.get_order(order_id)
        if order.status != OrderStatus.APPROVED:
            raise InvalidOrderTransitionError(
                f"Only APPROVED orders can be submitted; current={order.status}"
            )
        order.status = OrderStatus.SUBMITTED
        return self._save(order)

    def mark_filled(self, order_id: str) -> Order:
        order = self.get_order(order_id)
        if order.status != OrderStatus.SUBMITTED:
            raise InvalidOrderTransitionError(
                f"Only SUBMITTED orders can be filled; current={order.status}"
            )
        order.status = OrderStatus.FILLED
        return self._save(order)

    def cancel(self, order_id: str) -> Order:
        order = self.get_order(order_id)
        if order.status not in {OrderStatus.APPROVED, OrderStatus.SUBMITTED}:
            raise InvalidOrderTransitionError(
                f"Order cannot be cancelled from state {order.status}"
            )
        order.status = OrderStatus.CANCELLED
        return self._save(order)
