"""Fail-closed routing for market-specific engines."""

from __future__ import annotations

from dataclasses import dataclass

from market_domains.models import MarketDomain, MarketEvidence


class DomainRoutingError(RuntimeError):
    pass


@dataclass(frozen=True)
class DomainRoute:
    domain: MarketDomain
    engine_name: str


ROUTES = {
    MarketDomain.INDIA: DomainRoute(MarketDomain.INDIA, "india-engine"),
    MarketDomain.FOREX: DomainRoute(MarketDomain.FOREX, "forex-engine"),
    MarketDomain.CRYPTO: DomainRoute(MarketDomain.CRYPTO, "crypto-engine"),
    MarketDomain.INTERNATIONAL: DomainRoute(MarketDomain.INTERNATIONAL, "international-engine"),
}


class MarketDomainRouter:
    def route(self, evidence: MarketEvidence, requested_domain: MarketDomain) -> DomainRoute:
        if evidence.domain != requested_domain:
            raise DomainRoutingError(
                f"cross-domain evidence blocked: evidence={evidence.domain.value} "
                f"requested={requested_domain.value}"
            )
        if not evidence.executable:
            raise DomainRoutingError(
                f"non-verified evidence blocked: status={evidence.status.value}"
            )
        try:
            return ROUTES[requested_domain]
        except KeyError as exc:
            raise DomainRoutingError(f"unsupported market domain: {requested_domain}") from exc
