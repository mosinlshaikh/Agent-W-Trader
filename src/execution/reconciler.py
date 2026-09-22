"""Order reconciliation between local persistence and broker state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from domain.models import Order, OrderStatus


@dataclass(frozen=True)
class BrokerOrderState:
    broker_order_id: str
    status: OrderStatus
    fill_price: float | None = None


@dataclass(frozen=True)
class ReconciliationResult:
    order_id: str
    changed: bool
    previous_status: OrderStatus
    current_status: OrderStatus
    reason: str


class OrderReconciler:
    """Reconciles persisted orders against externally reported broker states."""

    def reconcile(
        self,
        orders: Iterable[Order],
        broker_states: dict[str, BrokerOrderState],
    ) -> list[ReconciliationResult]:
        results: list[ReconciliationResult] = []
        for order in orders:
            previous = order.status
            if not order.broker_order_id:
                results.append(
                    ReconciliationResult(
                        order_id=order.id,
                        changed=False,
                        previous_status=previous,
                        current_status=previous,
                        reason="order has no broker identifier",
                    )
                )
                continue

            remote = broker_states.get(order.broker_order_id)
            if remote is None:
                results.append(
                    ReconciliationResult(
                        order_id=order.id,
                        changed=False,
                        previous_status=previous,
                        current_status=previous,
                        reason="broker order not found",
                    )
                )
                continue

            allowed = {
                OrderStatus.SUBMITTED: {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED},
                OrderStatus.APPROVED: {OrderStatus.SUBMITTED, OrderStatus.REJECTED},
            }
            if remote.status == previous:
                changed = False
                reason = "local and broker states match"
            elif remote.status in allowed.get(previous, set()):
                order.status = remote.status
                if remote.fill_price is not None:
                    order.fill_price = remote.fill_price
                changed = True
                reason = "local order updated from broker state"
            else:
                changed = False
                reason = "unsafe or regressive broker transition ignored"

            results.append(
                ReconciliationResult(
                    order_id=order.id,
                    changed=changed,
                    previous_status=previous,
                    current_status=order.status,
                    reason=reason,
                )
            )
        return results
