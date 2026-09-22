"""Typed domain models for orders, risk decisions, and execution state."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    RISK_REJECTED = "RISK_REJECTED"
    APPROVED = "APPROVED"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    side: OrderSide
    quantity: int = Field(gt=0)
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = Field(default=None, gt=0)
    stop_loss_price: float = Field(gt=0)
    reference_price: float = Field(gt=0)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        symbol = value.strip().upper()
        if not symbol.replace("-", "").replace("&", "").isalnum():
            raise ValueError("symbol contains unsupported characters")
        return symbol

    @model_validator(mode="after")
    def validate_order_prices(self):
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("limit_price is required for LIMIT orders")
        if self.side == OrderSide.BUY and self.stop_loss_price >= self.reference_price:
            raise ValueError("BUY stop loss must be below reference price")
        if self.side == OrderSide.SELL and self.stop_loss_price <= self.reference_price:
            raise ValueError("SELL stop loss must be above reference price")
        return self


class RiskDecision(BaseModel):
    approved: bool
    reason: str
    estimated_risk_amount: float = Field(ge=0)
    max_allowed_risk_amount: float = Field(ge=0)


class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    request: OrderRequest
    status: OrderStatus = OrderStatus.CREATED
    risk_decision: Optional[RiskDecision] = None
    broker_order_id: Optional[str] = None
    fill_price: Optional[float] = Field(default=None, gt=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
