from datetime import datetime,timedelta,timezone
import pytest
from market_domains.models import MarketDomain
from market_intelligence.market_data import MarketDataGuard,MarketDataRejected,MarketSnapshot
from market_intelligence.candles import Candle,CandleIntelligence,CandleSignal

def snap(**kw):
 d=dict(domain=MarketDomain.INDIA,instrument="NIFTY",provider="test",observed_at=datetime.now(timezone.utc),bid=24999,ask=25001,last=25000,volume=100);d.update(kw);return MarketSnapshot(**d)

def test_fresh_quote_passes(): assert MarketDataGuard().verify(snap()).last==25000

def test_stale_quote_fails_closed():
 with pytest.raises(MarketDataRejected,match="stale"): MarketDataGuard().verify(snap(observed_at=datetime.now(timezone.utc)-timedelta(seconds=10)))

def test_crossed_quote_rejected():
 with pytest.raises(MarketDataRejected,match="crossed"): MarketDataGuard().verify(snap(bid=25002,ask=25001))

@pytest.mark.parametrize("domain",[MarketDomain.INDIA,MarketDomain.FOREX,MarketDomain.CRYPTO,MarketDomain.INTERNATIONAL])
def test_candle_engine_is_domain_aware(domain):
 now=datetime.now(timezone.utc); c=Candle(domain=domain,instrument="TEST",timeframe="1m",opened_at=now-timedelta(minutes=1),closed_at=now,open=100,high=112,low=98,close=110,volume=10)
 a=CandleIntelligence().analyze(c); assert a.signal==CandleSignal.BULLISH; assert a.body_pct>0

def test_invalid_ohlc_is_rejected():
 now=datetime.now(timezone.utc);c=Candle(domain=MarketDomain.CRYPTO,instrument="BTCUSD",timeframe="1m",opened_at=now-timedelta(minutes=1),closed_at=now,open=100,high=99,low=90,close=105)
 with pytest.raises(ValueError,match="invalid OHLC"): CandleIntelligence().analyze(c)
