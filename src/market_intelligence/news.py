from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from pydantic import BaseModel, Field
from market_domains.models import MarketDomain

class NewsStatus(str,Enum): VERIFIED="VERIFIED"; STALE="STALE"; CONFLICTED="CONFLICTED"; DUPLICATE="DUPLICATE"; INSUFFICIENT="INSUFFICIENT"
class NewsImpact(str,Enum): POSITIVE="POSITIVE"; NEGATIVE="NEGATIVE"; NEUTRAL="NEUTRAL"; UNKNOWN="UNKNOWN"

class NewsEvidence(BaseModel):
    domain: MarketDomain
    headline: str
    source: str
    published_at: datetime
    received_at: datetime=Field(default_factory=lambda:datetime.now(timezone.utc))
    related_instruments: list[str]=Field(default_factory=list)
    impact: NewsImpact=NewsImpact.UNKNOWN
    source_reference: str
    factual_claims: list[str]=Field(default_factory=list)

    @property
    def fingerprint(self)->str:
        normalized=" ".join(self.headline.lower().split())
        return sha256(f"{self.domain.value}|{normalized}".encode()).hexdigest()

class NewsDecision(BaseModel):
    status: NewsStatus
    executable: bool
    reason: str
    fingerprint: str

class NewsVerifier:
    def __init__(self,max_age_seconds:int=3600): self.max_age_seconds=max_age_seconds; self._seen:set[str]=set()
    def verify(self,item:NewsEvidence,now:datetime|None=None)->NewsDecision:
        now=now or datetime.now(timezone.utc)
        if item.published_at.tzinfo is None: return self._decision(item,NewsStatus.INSUFFICIENT,False,"published timestamp is not timezone-aware")
        if not item.source.strip() or not item.source_reference.strip(): return self._decision(item,NewsStatus.INSUFFICIENT,False,"source provenance missing")
        if not item.related_instruments: return self._decision(item,NewsStatus.INSUFFICIENT,False,"affected instruments missing")
        age=(now-item.published_at).total_seconds()
        if age< -60: return self._decision(item,NewsStatus.INSUFFICIENT,False,"future-dated news")
        if age>self.max_age_seconds: return self._decision(item,NewsStatus.STALE,False,"news outside freshness window")
        if item.fingerprint in self._seen: return self._decision(item,NewsStatus.DUPLICATE,False,"duplicate news event")
        self._seen.add(item.fingerprint)
        return self._decision(item,NewsStatus.VERIFIED,True,"provenance and freshness checks passed")
    def conflict(self,left:NewsEvidence,right:NewsEvidence)->NewsDecision:
        same=set(map(str.upper,left.related_instruments)) & set(map(str.upper,right.related_instruments))
        opposed={left.impact,right.impact}=={NewsImpact.POSITIVE,NewsImpact.NEGATIVE}
        if left.domain==right.domain and same and opposed:
            return self._decision(left,NewsStatus.CONFLICTED,False,"material sources disagree on directional impact")
        return self._decision(left,NewsStatus.INSUFFICIENT,False,"no deterministic conflict established")
    @staticmethod
    def _decision(item,status,executable,reason): return NewsDecision(status=status,executable=executable,reason=reason,fingerprint=item.fingerprint)
