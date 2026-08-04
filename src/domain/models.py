"""Typed domain models for orders, risk decisions, and execution state."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("limit_price")
    @classmethod
    def require_limit_price_for_limit_order(cls, value: Optional[float], info):
        order_type = info.data.get("order_type")
        if order_type == OrderType.LIMIT and value is None:
            raise ValueError("limit_price is required for LIMIT orders")
        return value


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
