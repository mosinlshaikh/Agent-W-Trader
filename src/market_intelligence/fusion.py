from __future__ import annotations
from enum import Enum
from pydantic import BaseModel
from market_domains.models import MarketDomain
from .candles import CandleAnalysis
from .news import NewsDecision,NewsStatus

class FusionState(str,Enum): READY="READY"; BLOCKED="BLOCKED"
class IntelligenceFusion(BaseModel):
    domain: MarketDomain
    instrument: str
    state: FusionState
    reasons: list[str]

class IntelligenceFusionEngine:
    """Combines verified facts without inventing a trade recommendation."""
    def combine(self,domain:MarketDomain,instrument:str,candle:CandleAnalysis,news:NewsDecision)->IntelligenceFusion:
        reasons=[f"candle={candle.signal.value}",f"news={news.status.value}"]
        if news.status!=NewsStatus.VERIFIED or not news.executable:
            return IntelligenceFusion(domain=domain,instrument=instrument.upper(),state=FusionState.BLOCKED,reasons=reasons+["news evidence not execution-grade"])
        return IntelligenceFusion(domain=domain,instrument=instrument.upper(),state=FusionState.READY,reasons=reasons+["verified facts ready for strategy agents"])
