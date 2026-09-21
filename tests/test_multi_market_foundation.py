from datetime import datetime, timezone

import pytest

from market_domains.models import EvidenceStatus, MarketDomain, MarketEvidence
from market_domains.router import DomainRoutingError, MarketDomainRouter


def evidence(domain=MarketDomain.INDIA, status=EvidenceStatus.VERIFIED):
    return MarketEvidence(
        domain=domain,
        instrument="NIFTY",
        evidence_type="quote",
        provider="certified-test-feed",
        observed_at=datetime.now(timezone.utc),
        status=status,
        value={"price": 25000},
        provenance="provider-event:test-1",
    )


@pytest.mark.parametrize(
    "domain",
    [
        MarketDomain.INDIA,
        MarketDomain.FOREX,
        MarketDomain.CRYPTO,
        MarketDomain.INTERNATIONAL,
    ],
)
def test_all_market_domains_have_isolated_routes(domain):
    item = evidence(domain=domain)
    route = MarketDomainRouter().route(item, domain)
    assert route.domain == domain


def test_cross_market_evidence_fails_closed():
    item = evidence(domain=MarketDomain.CRYPTO)
    with pytest.raises(DomainRoutingError, match="cross-domain evidence blocked"):
        MarketDomainRouter().route(item, MarketDomain.INDIA)


@pytest.mark.parametrize(
    "status",
    [
        EvidenceStatus.STALE,
        EvidenceStatus.CONFLICTED,
        EvidenceStatus.INSUFFICIENT,
        EvidenceStatus.BLOCKED,
    ],
)
def test_unverified_evidence_cannot_enter_execution_path(status):
    item = evidence(status=status)
    with pytest.raises(DomainRoutingError, match="non-verified evidence blocked"):
        MarketDomainRouter().route(item, MarketDomain.INDIA)


def test_evidence_requires_provenance():
    with pytest.raises(ValueError):
        MarketEvidence(
            domain=MarketDomain.FOREX,
            instrument="EURUSD",
            evidence_type="quote",
            provider="feed",
            observed_at=datetime.now(timezone.utc),
            status=EvidenceStatus.VERIFIED,
            value=1.1,
            provenance="",
        )
