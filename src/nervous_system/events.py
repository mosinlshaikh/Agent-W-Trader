from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field
from market_domains.models import MarketDomain, MarketEvidence

class EventKind(str, Enum):
    MARKET = "MARKET"
    CANDLE = "CANDLE"
    NEWS = "NEWS"
    BROKER = "BROKER"
    RISK = "RISK"
    PORTFOLIO = "PORTFOLIO"

class NervousSystemEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    kind: EventKind
    domain: MarketDomain
    instrument: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence: MarketEvidence
    payload: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        self.instrument = self.instrument.strip().upper()
        if not self.instrument:
            raise ValueError("instrument is required")
        if self.evidence.domain != self.domain:
            raise ValueError("event/evidence domain mismatch")
        if self.evidence.instrument != self.instrument:
            raise ValueError("event/evidence instrument mismatch")
