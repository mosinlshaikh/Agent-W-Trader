"""Fail-closed market-data freshness validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


class StaleMarketDataError(RuntimeError):
    """Raised when execution is attempted using stale or future-dated data."""


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    price: float
    observed_at: datetime


class MarketDataGuard:
    def __init__(self, max_age_seconds: float = 5.0) -> None:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        self.max_age_seconds = max_age_seconds

    def validate(self, snapshot: MarketSnapshot, now: datetime | None = None) -> None:
        if snapshot.price <= 0:
            raise StaleMarketDataError("market price must be positive")
        current = now or datetime.now(timezone.utc)
        observed = snapshot.observed_at
        if observed.tzinfo is None:
            raise StaleMarketDataError("market timestamp must be timezone-aware")
        age = (current - observed).total_seconds()
        if age < -1:
            raise StaleMarketDataError("market timestamp is in the future")
        if age > self.max_age_seconds:
            raise StaleMarketDataError(
                f"market data is stale: age={age:.3f}s limit={self.max_age_seconds:.3f}s"
            )
