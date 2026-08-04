"""Risk-gated order lifecycle for paper trading and broker integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from domain.models import Order, OrderRequest, OrderStatus
from risk.risk_engine import RiskEngine


class OrderNotFoundError(KeyError):
    """Raised when an order identifier cannot be resolved."""


class InvalidOrderTransitionError(RuntimeError):
    """Raised when an unsafe order-state transition is requested."""


class OrderManager:
    """Creates orders and enforces deterministic pre-trade risk approval.

    This component does not submit live broker orders yet. Approved orders remain
    explicitly marked as APPROVED until a broker execution service submits them.
    """

    def __init__(self, risk_engine: RiskEngine):
        self.risk_engine = risk_engine
        self._orders: Dict[str, Order] = {}

    def create_order(self, request: OrderRequest) -> Order:
        order = Order(request=request)
        decision = self.risk_engine.evaluate(request)
        order.risk_decision = decision
        order.status = (
            OrderStatus.APPROVED if decision.approved else OrderStatus.RISK_REJECTED
        )
        order.updated_at = datetime.now(timezone.utc)
        self._orders[order.id] = order
        return order

    def get_order(self, order_id: str) -> Order:
        try:
            return self._orders[order_id]
        except KeyError as exc:
            raise OrderNotFoundError(order_id) from exc

    def list_orders(self) -> list[Order]:
        return list(self._orders.values())

    def mark_submitted(self, order_id: str) -> Order:
        order = self.get_order(order_id)
        if order.status != OrderStatus.APPROVED:
            raise InvalidOrderTransitionError(
                f"Only APPROVED orders can be submitted; current={order.status}"
            )
        order.status = OrderStatus.SUBMITTED
        order.updated_at = datetime.now(timezone.utc)
        return order

    def mark_filled(self, order_id: str) -> Order:
        order = self.get_order(order_id)
        if order.status != OrderStatus.SUBMITTED:
            raise InvalidOrderTransitionError(
                f"Only SUBMITTED orders can be filled; current={order.status}"
            )
        order.status = OrderStatus.FILLED
        order.updated_at = datetime.now(timezone.utc)
        return order

    def cancel(self, order_id: str) -> Order:
        order = self.get_order(order_id)
        if order.status not in {OrderStatus.APPROVED, OrderStatus.SUBMITTED}:
            raise InvalidOrderTransitionError(
                f"Order cannot be cancelled from state {order.status}"
            )
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(timezone.utc)
        return order
