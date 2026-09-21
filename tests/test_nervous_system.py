from datetime import datetime, timezone
import pytest
from market_domains.models import EvidenceStatus, MarketDomain, MarketEvidence
from nervous_system.bus import NervousSystemBus, NervousSystemRejected
from nervous_system.events import EventKind, NervousSystemEvent

def make_evidence(domain=MarketDomain.INDIA, instrument="NIFTY", status=EvidenceStatus.VERIFIED):
    return MarketEvidence(domain=domain,instrument=instrument,evidence_type="QUOTE",provider="test-feed",observed_at=datetime.now(timezone.utc),status=status,value={"price":25000},provenance="test:event")

def test_event_reaches_only_matching_domain_and_kind():
    bus=NervousSystemBus(); seen=[]
    bus.subscribe(MarketDomain.INDIA, EventKind.MARKET, lambda event: seen.append("india"))
    bus.subscribe(MarketDomain.CRYPTO, EventKind.MARKET, lambda event: seen.append("crypto"))
    ev=NervousSystemEvent(kind=EventKind.MARKET,domain=MarketDomain.INDIA,instrument="NIFTY",evidence=make_evidence())
    assert bus.publish(ev)==1
    assert seen==["india"]

def test_stale_event_fails_closed_before_agent_dispatch():
    bus=NervousSystemBus(); seen=[]
    bus.subscribe(MarketDomain.INDIA, EventKind.NEWS, lambda event: seen.append(event))
    ev=NervousSystemEvent(kind=EventKind.NEWS,domain=MarketDomain.INDIA,instrument="NIFTY",evidence=make_evidence(status=EvidenceStatus.STALE))
    with pytest.raises(NervousSystemRejected): bus.publish(ev)
    assert seen==[]

def test_event_cannot_carry_cross_domain_evidence():
    with pytest.raises(ValueError, match="domain mismatch"):
        NervousSystemEvent(kind=EventKind.MARKET,domain=MarketDomain.FOREX,instrument="BTCUSD",evidence=make_evidence(domain=MarketDomain.CRYPTO,instrument="BTCUSD"))

def test_event_cannot_relabel_instrument():
    with pytest.raises(ValueError, match="instrument mismatch"):
        NervousSystemEvent(kind=EventKind.MARKET,domain=MarketDomain.INDIA,instrument="BANKNIFTY",evidence=make_evidence(instrument="NIFTY"))
