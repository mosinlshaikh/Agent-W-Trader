"""Typed portfolio-ledger events and immutable financial state models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class LedgerEventType(str, Enum):
    CASH_DEPOSIT = "CASH_DEPOSIT"
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"
    BUY_FILL = "BUY_FILL"
    SELL_FILL = "SELL_FILL"
    FEE = "FEE"


class LedgerEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: LedgerEventType
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str | None = None
    quantity: int = Field(default=0, ge=0)
    price: float = Field(default=0.0, ge=0)
    amount: float = 0.0
    reference_id: str | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "LedgerEvent":
        if self.event_type in {LedgerEventType.BUY_FILL, LedgerEventType.SELL_FILL}:
            if not self.symbol or self.quantity <= 0 or self.price <= 0:
                raise ValueError("fill events require symbol, positive quantity, and price")
        if self.event_type in {
            LedgerEventType.CASH_DEPOSIT,
            LedgerEventType.CASH_WITHDRAWAL,
            LedgerEventType.FEE,
        } and self.amount <= 0:
            raise ValueError("cash and fee events require positive amount")
        if self.symbol:
            self.symbol = self.symbol.strip().upper()
        return self


class PositionState(BaseModel):
    symbol: str
    quantity: int = 0
    average_price: float = 0.0
    realized_pnl: float = 0.0


class PortfolioState(BaseModel):
    cash_balance: float = 0.0
    fees_paid: float = 0.0
    realized_pnl: float = 0.0
    positions: dict[str, PositionState] = Field(default_factory=dict)
    last_event_id: str | None = None
