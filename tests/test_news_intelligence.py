from datetime import datetime,timedelta,timezone
from market_domains.models import MarketDomain
from market_intelligence.news import NewsDecision,NewsEvidence,NewsImpact,NewsStatus,NewsVerifier
from market_intelligence.fusion import FusionState,IntelligenceFusionEngine
from market_intelligence.candles import CandleAnalysis,CandleSignal

def item(**kw):
 d=dict(domain=MarketDomain.INDIA,headline="Company reports material exchange filing",source="official-feed",published_at=datetime.now(timezone.utc),related_instruments=["ABC"],impact=NewsImpact.NEUTRAL,source_reference="ref:1",factual_claims=["filing received"]);d.update(kw);return NewsEvidence(**d)

def test_verified_news_requires_provenance_freshness_and_instrument(): assert NewsVerifier().verify(item()).status==NewsStatus.VERIFIED

def test_duplicate_news_cannot_trigger_twice():
 v=NewsVerifier(); n=item(); assert v.verify(n).executable; assert v.verify(n).status==NewsStatus.DUPLICATE

def test_stale_news_fails_closed(): assert NewsVerifier().verify(item(published_at=datetime.now(timezone.utc)-timedelta(hours=2))).status==NewsStatus.STALE

def test_missing_source_reference_fails_closed(): assert NewsVerifier().verify(item(source_reference="")).status==NewsStatus.INSUFFICIENT

def test_conflicting_directional_sources_are_quarantined():
 v=NewsVerifier(); a=item(impact=NewsImpact.POSITIVE,source_reference="a"); b=item(headline="Second source",impact=NewsImpact.NEGATIVE,source_reference="b")
 assert v.conflict(a,b).status==NewsStatus.CONFLICTED

def test_fusion_blocks_unverified_news():
 candle=CandleAnalysis(signal=CandleSignal.BULLISH,body_pct=50,range_pct=1,upper_wick_pct=25,lower_wick_pct=25,reason="deterministic")
 news=NewsDecision(status=NewsStatus.CONFLICTED,executable=False,reason="conflict",fingerprint="x")
 result=IntelligenceFusionEngine().combine(MarketDomain.INDIA,"ABC",candle,news); assert result.state==FusionState.BLOCKED
