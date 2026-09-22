"""Typed evidence primitives shared by isolated market-domain engines."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class MarketDomain(str, Enum):
    INDIA = "INDIA"
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"
    INTERNATIONAL = "INTERNATIONAL"


class EvidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    STALE = "STALE"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT = "INSUFFICIENT"
    BLOCKED = "BLOCKED"


class MarketEvidence(BaseModel):
    """A trade-relevant fact with provenance.

    Evidence is intentionally domain-scoped so an agent cannot accidentally
    treat data from one market as executable evidence for another.
    """

    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    domain: MarketDomain
    instrument: str
    evidence_type: str
    provider: str
    observed_at: datetime
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: EvidenceStatus
    value: Any = None
    provenance: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_evidence(self) -> "MarketEvidence":
        self.instrument = self.instrument.strip().upper()
        self.evidence_type = self.evidence_type.strip().upper()
        self.provider = self.provider.strip()
        self.provenance = self.provenance.strip()
        if not self.instrument:
            raise ValueError("instrument is required")
        if not self.evidence_type:
            raise ValueError("evidence_type is required")
        if not self.provider:
            raise ValueError("provider is required")
        if not self.provenance:
            raise ValueError("provenance is required")
        if self.observed_at.tzinfo is None or self.ingested_at.tzinfo is None:
            raise ValueError("evidence timestamps must be timezone-aware")
        return self

    @property
    def executable(self) -> bool:
        return self.status == EvidenceStatus.VERIFIED
