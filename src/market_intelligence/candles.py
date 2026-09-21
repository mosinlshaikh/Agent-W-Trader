from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from market_domains.models import MarketDomain

class CandleSignal(str,Enum):
    BULLISH="BULLISH"; BEARISH="BEARISH"; NEUTRAL="NEUTRAL"

class Candle(BaseModel):
    domain: MarketDomain
    instrument: str
    timeframe: str
    opened_at: datetime
    closed_at: datetime
    open: float; high: float; low: float; close: float; volume: float=0

class CandleAnalysis(BaseModel):
    signal:CandleSignal
    body_pct:float
    range_pct:float
    upper_wick_pct:float
    lower_wick_pct:float
    reason:str

class CandleIntelligence:
    """Deterministic candle facts. AI may interpret these facts but cannot rewrite them."""
    def analyze(self,c:Candle)->CandleAnalysis:
        if min(c.open,c.high,c.low,c.close)<=0: raise ValueError("candle prices must be positive")
        if c.high < max(c.open,c.close) or c.low > min(c.open,c.close) or c.high < c.low: raise ValueError("invalid OHLC geometry")
        if c.closed_at <= c.opened_at: raise ValueError("candle close must follow open")
        rng=c.high-c.low
        if rng==0:
            return CandleAnalysis(signal=CandleSignal.NEUTRAL,body_pct=0,range_pct=0,upper_wick_pct=0,lower_wick_pct=0,reason="zero-range candle")
        body=abs(c.close-c.open)
        upper=c.high-max(c.open,c.close); lower=min(c.open,c.close)-c.low
        signal=CandleSignal.BULLISH if c.close>c.open else CandleSignal.BEARISH if c.close<c.open else CandleSignal.NEUTRAL
        return CandleAnalysis(signal=signal,body_pct=body/rng*100,range_pct=rng/c.open*100,upper_wick_pct=upper/rng*100,lower_wick_pct=lower/rng*100,reason="deterministic OHLC structure")
