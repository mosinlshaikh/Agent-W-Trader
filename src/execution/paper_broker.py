"""Deterministic paper broker used before any live-money integration."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from domain.models import Order, OrderSide, OrderStatus
from market.data_guard import MarketDataGuard, MarketSnapshot


@dataclass(frozen=True)
class PaperFill:
    broker_order_id: str
    fill_price: float
    quantity: int


class PaperBroker:
    def __init__(self, data_guard: MarketDataGuard, slippage_bps: float = 2.0) -> None:
        if slippage_bps < 0:
            raise ValueError("slippage_bps cannot be negative")
        self.data_guard = data_guard
        self.slippage_bps = slippage_bps

    def execute(self, order: Order, snapshot: MarketSnapshot) -> PaperFill:
        if order.status != OrderStatus.APPROVED:
            raise RuntimeError(f"paper broker requires APPROVED order, got {order.status}")
        if snapshot.symbol.strip().upper() != order.request.symbol:
            raise ValueError("snapshot symbol does not match order symbol")
        self.data_guard.validate(snapshot)
        direction = 1 if order.request.side == OrderSide.BUY else -1
        multiplier = 1 + direction * (self.slippage_bps / 10_000)
        fill_price = round(snapshot.price * multiplier, 4)
        return PaperFill(
            broker_order_id=f"PAPER-{uuid4()}",
            fill_price=fill_price,
            quantity=order.request.quantity,
        )
