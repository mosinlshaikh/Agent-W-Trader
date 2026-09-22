from __future__ import annotations
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from market_domains.models import MarketDomain

class MarketDataRejected(RuntimeError): pass

class MarketSnapshot(BaseModel):
    domain: MarketDomain
    instrument: str
    provider: str
    observed_at: datetime
    bid: float | None = None
    ask: float | None = None
    last: float
    volume: float | None = None
    metadata: dict = Field(default_factory=dict)

class MarketDataGuard:
    def __init__(self,max_age_seconds:float=5.0,max_future_seconds:float=1.0):
        self.max_age_seconds=max_age_seconds; self.max_future_seconds=max_future_seconds
    def verify(self,snapshot:MarketSnapshot,now:datetime|None=None)->MarketSnapshot:
        now=now or datetime.now(timezone.utc)
        if snapshot.observed_at.tzinfo is None: raise MarketDataRejected("timestamp must be timezone-aware")
        age=(now-snapshot.observed_at).total_seconds()
        if age < -self.max_future_seconds: raise MarketDataRejected("future market data")
        if age > self.max_age_seconds: raise MarketDataRejected("stale market data")
        if snapshot.last <= 0: raise MarketDataRejected("non-positive last price")
        if snapshot.bid is not None and snapshot.bid <= 0: raise MarketDataRejected("non-positive bid")
        if snapshot.ask is not None and snapshot.ask <= 0: raise MarketDataRejected("non-positive ask")
        if snapshot.bid is not None and snapshot.ask is not None and snapshot.bid > snapshot.ask: raise MarketDataRejected("crossed quote")
        return snapshot
