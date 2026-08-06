"""Deterministic event-driven exchange simulator for realistic paper execution."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from enum import Enum
from itertools import count
from typing import Iterable
from uuid import uuid4


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SimOrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class SimOrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class BookLevel:
    price: float
    quantity: int

    def __post_init__(self) -> None:
        if self.price <= 0 or self.quantity <= 0:
            raise ValueError("book levels require positive price and quantity")


@dataclass
class SimOrder:
    symbol: str
    side: Side
    quantity: int
    order_type: SimOrderType
    limit_price: float | None = None
    order_id: str = field(default_factory=lambda: str(uuid4()))
    submitted_at_ms: int = 0
    active_at_ms: int = 0
    remaining_quantity: int = 0
    status: SimOrderStatus = SimOrderStatus.PENDING
    rejection_reason: str | None = None

    def __post_init__(self) -> None:
        self.symbol = self.symbol.strip().upper()
        if not self.symbol or self.quantity <= 0:
            raise ValueError("order requires symbol and positive quantity")
        if self.order_type == SimOrderType.LIMIT and (self.limit_price is None or self.limit_price <= 0):
            raise ValueError("limit orders require positive limit_price")
        if self.order_type == SimOrderType.MARKET and self.limit_price is not None:
            raise ValueError("market orders cannot define limit_price")
        self.remaining_quantity = self.quantity


@dataclass(frozen=True)
class Fill:
    order_id: str
    symbol: str
    side: Side
    quantity: int
    price: float
    occurred_at_ms: int


@dataclass(frozen=True)
class ExchangeEvent:
    occurred_at_ms: int
    event_type: str
    order_id: str | None
    detail: str


class UnknownOrderError(KeyError):
    pass


class ExchangeSimulator:
    """Price-time-priority exchange model with latency and fail-closed controls."""

    def __init__(
        self,
        *,
        latency_ms: int = 25,
        market_impact_bps_per_full_level: float = 1.0,
    ) -> None:
        if latency_ms < 0 or market_impact_bps_per_full_level < 0:
            raise ValueError("latency and impact must be non-negative")
        self.latency_ms = latency_ms
        self.market_impact_bps_per_full_level = market_impact_bps_per_full_level
        self.now_ms = 0
        self.halted = False
        self.circuit_lower: float | None = None
        self.circuit_upper: float | None = None
        self.bids: list[BookLevel] = []
        self.asks: list[BookLevel] = []
        self.orders: dict[str, SimOrder] = {}
        self.fills: list[Fill] = []
        self.events: list[ExchangeEvent] = []
        self._pending: list[tuple[int, int, str, str, object | None]] = []
        self._sequence = count()
        self._resting_buy: list[tuple[float, int, str]] = []
        self._resting_sell: list[tuple[float, int, str]] = []

    def seed_book(self, *, bids: Iterable[BookLevel], asks: Iterable[BookLevel]) -> None:
        self.bids = sorted(list(bids), key=lambda x: x.price, reverse=True)
        self.asks = sorted(list(asks), key=lambda x: x.price)
        if self.bids and self.asks and self.bids[0].price >= self.asks[0].price:
            raise ValueError("seeded book must not be crossed")

    def set_circuit_limits(self, lower: float, upper: float) -> None:
        if lower <= 0 or upper <= lower:
            raise ValueError("invalid circuit limits")
        self.circuit_lower, self.circuit_upper = lower, upper

    def set_halted(self, halted: bool) -> None:
        self.halted = bool(halted)
        self.events.append(ExchangeEvent(self.now_ms, "HALT" if halted else "RESUME", None, "exchange state changed"))

    def submit(self, order: SimOrder) -> str:
        if order.order_id in self.orders:
            raise ValueError("duplicate order_id")
        order.submitted_at_ms = self.now_ms
        order.active_at_ms = self.now_ms + self.latency_ms
        self.orders[order.order_id] = order
        self._schedule(order.active_at_ms, "ACTIVATE", order.order_id, None)
        self.events.append(ExchangeEvent(self.now_ms, "SUBMITTED", order.order_id, f"active at {order.active_at_ms}ms"))
        return order.order_id

    def cancel(self, order_id: str) -> None:
        order = self._order(order_id)
        self._schedule(self.now_ms + self.latency_ms, "CANCEL", order_id, None)

    def replace(self, order_id: str, *, quantity: int, limit_price: float) -> None:
        if quantity <= 0 or limit_price <= 0:
            raise ValueError("replacement quantity and price must be positive")
        self._order(order_id)
        self._schedule(self.now_ms + self.latency_ms, "REPLACE", order_id, (quantity, limit_price))

    def advance_to(self, target_ms: int) -> None:
        if target_ms < self.now_ms:
            raise ValueError("time cannot move backwards")
        while self._pending and self._pending[0][0] <= target_ms:
            occurred_at, _, action, order_id, payload = heapq.heappop(self._pending)
            self.now_ms = occurred_at
            if action == "ACTIVATE":
                self._activate(self._order(order_id))
            elif action == "CANCEL":
                self._apply_cancel(self._order(order_id))
            elif action == "REPLACE":
                quantity, limit_price = payload  # type: ignore[misc]
                self._apply_replace(self._order(order_id), int(quantity), float(limit_price))
        self.now_ms = target_ms

    def _activate(self, order: SimOrder) -> None:
        if self.halted:
            self._reject(order, "TRADING_HALTED")
            return
        if order.limit_price is not None and not self._inside_circuit(order.limit_price):
            self._reject(order, "PRICE_OUTSIDE_CIRCUIT")
            return
        order.status = SimOrderStatus.OPEN
        self.events.append(ExchangeEvent(self.now_ms, "ACTIVE", order.order_id, "order entered matching engine"))
        self._match(order)
        if order.remaining_quantity > 0 and order.order_type == SimOrderType.LIMIT:
            self._rest(order)
        elif order.remaining_quantity > 0 and order.order_type == SimOrderType.MARKET:
            self._reject_remainder(order, "INSUFFICIENT_LIQUIDITY")

    def _match(self, order: SimOrder) -> None:
        levels = self.asks if order.side == Side.BUY else self.bids
        consumed = 0
        while order.remaining_quantity > 0 and levels:
            level = levels[0]
            if order.order_type == SimOrderType.LIMIT:
                crosses = level.price <= float(order.limit_price) if order.side == Side.BUY else level.price >= float(order.limit_price)
                if not crosses:
                    break
            fill_qty = min(order.remaining_quantity, level.quantity)
            impact = level.price * (self.market_impact_bps_per_full_level / 10_000) * consumed
            price = level.price + impact if order.side == Side.BUY else level.price - impact
            if not self._inside_circuit(price):
                self._reject_remainder(order, "MARKET_IMPACT_OUTSIDE_CIRCUIT")
                break
            self._record_fill(order, fill_qty, price)
            remaining_level = level.quantity - fill_qty
            if remaining_level:
                levels[0] = BookLevel(level.price, remaining_level)
            else:
                levels.pop(0)
                consumed += 1

    def _rest(self, order: SimOrder) -> None:
        sequence = next(self._sequence)
        if order.side == Side.BUY:
            heapq.heappush(self._resting_buy, (-float(order.limit_price), sequence, order.order_id))
        else:
            heapq.heappush(self._resting_sell, (float(order.limit_price), sequence, order.order_id))
        self.events.append(ExchangeEvent(self.now_ms, "RESTING", order.order_id, "price-time priority assigned"))

    def execute_external_trade(self, *, price: float, quantity: int, aggressor_side: Side) -> None:
        if price <= 0 or quantity <= 0 or self.halted or not self._inside_circuit(price):
            return
        heap = self._resting_sell if aggressor_side == Side.BUY else self._resting_buy
        remaining = quantity
        deferred: list[tuple[float, int, str]] = []
        while heap and remaining > 0:
            priority, sequence, order_id = heapq.heappop(heap)
            order = self._order(order_id)
            if order.status not in {SimOrderStatus.OPEN, SimOrderStatus.PARTIALLY_FILLED}:
                continue
            limit = float(order.limit_price)
            eligible = limit <= price if order.side == Side.SELL else limit >= price
            if not eligible:
                deferred.append((priority, sequence, order_id))
                break
            fill_qty = min(remaining, order.remaining_quantity)
            self._record_fill(order, fill_qty, limit)
            remaining -= fill_qty
            if order.remaining_quantity > 0:
                deferred.append((priority, sequence, order_id))
        for item in deferred:
            heapq.heappush(heap, item)

    def _apply_cancel(self, order: SimOrder) -> None:
        if order.status in {SimOrderStatus.FILLED, SimOrderStatus.CANCELLED, SimOrderStatus.REJECTED}:
            self.events.append(ExchangeEvent(self.now_ms, "CANCEL_REJECTED", order.order_id, "order already terminal"))
            return
        order.status = SimOrderStatus.CANCELLED
        self.events.append(ExchangeEvent(self.now_ms, "CANCELLED", order.order_id, "cancel won race"))

    def _apply_replace(self, order: SimOrder, quantity: int, limit_price: float) -> None:
        if order.status in {SimOrderStatus.FILLED, SimOrderStatus.CANCELLED, SimOrderStatus.REJECTED}:
            self.events.append(ExchangeEvent(self.now_ms, "REPLACE_REJECTED", order.order_id, "order already terminal"))
            return
        if quantity < order.quantity - order.remaining_quantity or not self._inside_circuit(limit_price):
            self.events.append(ExchangeEvent(self.now_ms, "REPLACE_REJECTED", order.order_id, "invalid replacement"))
            return
        filled = order.quantity - order.remaining_quantity
        order.quantity = quantity
        order.remaining_quantity = quantity - filled
        order.limit_price = limit_price
        order.status = SimOrderStatus.OPEN
        self._rest(order)
        self.events.append(ExchangeEvent(self.now_ms, "REPLACED", order.order_id, "priority reset"))

    def _record_fill(self, order: SimOrder, quantity: int, price: float) -> None:
        order.remaining_quantity -= quantity
        order.status = SimOrderStatus.FILLED if order.remaining_quantity == 0 else SimOrderStatus.PARTIALLY_FILLED
        fill = Fill(order.order_id, order.symbol, order.side, quantity, price, self.now_ms)
        self.fills.append(fill)
        self.events.append(ExchangeEvent(self.now_ms, "FILL", order.order_id, f"{quantity}@{price:.4f}"))

    def _reject(self, order: SimOrder, reason: str) -> None:
        order.status = SimOrderStatus.REJECTED
        order.rejection_reason = reason
        self.events.append(ExchangeEvent(self.now_ms, "REJECTED", order.order_id, reason))

    def _reject_remainder(self, order: SimOrder, reason: str) -> None:
        if order.remaining_quantity == order.quantity:
            self._reject(order, reason)
        else:
            order.rejection_reason = reason
            self.events.append(ExchangeEvent(self.now_ms, "REMAINDER_REJECTED", order.order_id, reason))

    def _inside_circuit(self, price: float) -> bool:
        if self.circuit_lower is not None and price < self.circuit_lower:
            return False
        if self.circuit_upper is not None and price > self.circuit_upper:
            return False
        return True

    def _schedule(self, occurred_at_ms: int, action: str, order_id: str, payload: object | None) -> None:
        heapq.heappush(self._pending, (occurred_at_ms, next(self._sequence), action, order_id, payload))

    def _order(self, order_id: str) -> SimOrder:
        try:
            return self.orders[order_id]
        except KeyError as exc:
            raise UnknownOrderError(order_id) from exc
