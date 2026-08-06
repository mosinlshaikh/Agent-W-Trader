"""Deterministic safety gate between strategy agents and order execution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from hashlib import sha256
from typing import Iterable, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from domain.models import OrderRequest, OrderSide, OrderType, RiskDecision
from risk.risk_engine import RiskEngine


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class StrategySignal(BaseModel):
    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    strategy: str = Field(min_length=1, max_length=64)
    symbol: str = Field(min_length=1, max_length=32)
    action: SignalAction
    confidence: float = Field(ge=0, le=1)
    quantity: int = Field(default=0, ge=0)
    reference_price: float = Field(gt=0)
    stop_loss_price: float | None = Field(default=None, gt=0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rationale: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("strategy", "symbol")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value cannot be blank")
        return normalized.upper()

    @model_validator(mode="after")
    def validate_trade_shape(self) -> "StrategySignal":
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware")
        if self.action != SignalAction.HOLD:
            if self.quantity <= 0 or self.stop_loss_price is None:
                raise ValueError("trade signals require quantity and stop loss")
            if self.action == SignalAction.BUY and self.stop_loss_price >= self.reference_price:
                raise ValueError("BUY stop loss must be below reference price")
            if self.action == SignalAction.SELL and self.stop_loss_price <= self.reference_price:
                raise ValueError("SELL stop loss must be above reference price")
        return self

    def fingerprint(self) -> str:
        raw = "|".join(
            [
                self.strategy,
                self.symbol,
                self.action.value,
                str(self.quantity),
                f"{self.reference_price:.8f}",
                f"{self.stop_loss_price or 0:.8f}",
            ]
        )
        return sha256(raw.encode("utf-8")).hexdigest()


class DecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPPRESSED = "SUPPRESSED"


class DecisionEvidence(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    signal_id: str
    status: DecisionStatus
    reason_code: str
    explanation: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float
    minimum_confidence: float
    fingerprint: str
    risk_decision: RiskDecision | None = None
    order_request: OrderRequest | None = None


class DecisionJournal(Protocol):
    def record_decision(self, signal: StrategySignal, evidence: DecisionEvidence, *, order_id: str | None = None) -> None: ...
    def is_quarantined(self, strategy: str) -> bool: ...
    def quarantine_reason(self, strategy: str) -> str | None: ...


class StrategyDecisionGate:
    """Fail-closed signal gate with duplicate, cooldown, position, risk, and worker checks."""

    def __init__(
        self,
        risk_engine: RiskEngine,
        *,
        minimum_confidence: float = 0.65,
        cooldown: timedelta = timedelta(minutes=5),
        maximum_signal_age: timedelta = timedelta(minutes=2),
        minimum_consensus_ratio: float = 0.60,
        decision_journal: DecisionJournal | None = None,
    ) -> None:
        if not 0 <= minimum_confidence <= 1:
            raise ValueError("minimum_confidence must be between 0 and 1")
        if cooldown.total_seconds() < 0 or maximum_signal_age.total_seconds() <= 0:
            raise ValueError("invalid timing controls")
        if not 0.5 <= minimum_consensus_ratio <= 1:
            raise ValueError("minimum_consensus_ratio must be between 0.5 and 1")
        self.risk_engine = risk_engine
        self.minimum_confidence = minimum_confidence
        self.cooldown = cooldown
        self.maximum_signal_age = maximum_signal_age
        self.minimum_consensus_ratio = minimum_consensus_ratio
        self.decision_journal = decision_journal
        self._seen_signal_ids: set[str] = set()
        self._seen_fingerprints: set[str] = set()
        self._last_approved: dict[tuple[str, str, SignalAction], datetime] = {}

    def evaluate(
        self,
        signal: StrategySignal,
        *,
        existing_position_quantity: int = 0,
        now: datetime | None = None,
    ) -> DecisionEvidence:
        evaluated_at = now or datetime.now(timezone.utc)
        if evaluated_at.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        fingerprint = signal.fingerprint()

        if self.decision_journal is not None and self.decision_journal.is_quarantined(signal.strategy):
            reason = self.decision_journal.quarantine_reason(signal.strategy) or "worker performance policy"
            return self._decision(signal, DecisionStatus.SUPPRESSED, "WORKER_QUARANTINED", f"Strategy worker is quarantined: {reason}", evaluated_at)
        if signal.signal_id in self._seen_signal_ids or fingerprint in self._seen_fingerprints:
            return self._decision(signal, DecisionStatus.SUPPRESSED, "DUPLICATE_SIGNAL", "Signal was already evaluated", evaluated_at)

        self._seen_signal_ids.add(signal.signal_id)
        self._seen_fingerprints.add(fingerprint)

        if signal.generated_at > evaluated_at + timedelta(seconds=5):
            return self._decision(signal, DecisionStatus.REJECTED, "FUTURE_SIGNAL", "Signal timestamp is in the future", evaluated_at)
        if evaluated_at - signal.generated_at > self.maximum_signal_age:
            return self._decision(signal, DecisionStatus.REJECTED, "STALE_SIGNAL", "Signal exceeded maximum permitted age", evaluated_at)
        if signal.action == SignalAction.HOLD:
            return self._decision(signal, DecisionStatus.SUPPRESSED, "HOLD_SIGNAL", "HOLD signals never create orders", evaluated_at)
        if signal.confidence < self.minimum_confidence:
            return self._decision(signal, DecisionStatus.REJECTED, "LOW_CONFIDENCE", "Confidence is below configured threshold", evaluated_at)
        if signal.action == SignalAction.BUY and existing_position_quantity > 0:
            return self._decision(signal, DecisionStatus.SUPPRESSED, "POSITION_ALREADY_OPEN", "Duplicate long exposure is suppressed", evaluated_at)
        if signal.action == SignalAction.SELL and existing_position_quantity <= 0:
            return self._decision(signal, DecisionStatus.SUPPRESSED, "NO_POSITION_TO_EXIT", "Sell signal has no long position to exit", evaluated_at)

        key = (signal.strategy, signal.symbol, signal.action)
        last_approved = self._last_approved.get(key)
        if last_approved is not None and evaluated_at - last_approved < self.cooldown:
            return self._decision(signal, DecisionStatus.SUPPRESSED, "COOLDOWN_ACTIVE", "Strategy-symbol cooldown is active", evaluated_at)

        order = OrderRequest(
            symbol=signal.symbol,
            side=OrderSide(signal.action.value),
            quantity=signal.quantity,
            order_type=OrderType.MARKET,
            stop_loss_price=float(signal.stop_loss_price),
            reference_price=signal.reference_price,
        )
        risk = self.risk_engine.evaluate(order)
        if not risk.approved:
            return self._decision(signal, DecisionStatus.REJECTED, "RISK_REJECTED", risk.reason, evaluated_at, risk_decision=risk, order_request=order)

        self._last_approved[key] = evaluated_at
        return self._decision(
            signal,
            DecisionStatus.APPROVED,
            "ALL_CHECKS_PASSED",
            "Signal passed confidence, freshness, position, cooldown, risk, and worker controls",
            evaluated_at,
            risk_decision=risk,
            order_request=order,
        )

    def evaluate_consensus(
        self,
        signals: Iterable[StrategySignal],
        *,
        existing_position_quantity: int = 0,
        now: datetime | None = None,
    ) -> list[DecisionEvidence]:
        items = list(signals)
        if not items:
            return []
        symbols = {item.symbol for item in items}
        if len(symbols) != 1:
            raise ValueError("consensus batch must contain one symbol")
        directional = [item for item in items if item.action != SignalAction.HOLD]
        if not directional:
            return [self.evaluate(item, existing_position_quantity=existing_position_quantity, now=now) for item in items]
        buy_count = sum(item.action == SignalAction.BUY for item in directional)
        sell_count = len(directional) - buy_count
        winning_action = SignalAction.BUY if buy_count > sell_count else SignalAction.SELL
        winning_count = max(buy_count, sell_count)
        ratio = winning_count / len(directional)
        evaluated_at = now or datetime.now(timezone.utc)
        if buy_count == sell_count or ratio < self.minimum_consensus_ratio:
            return [
                self._decision(item, DecisionStatus.REJECTED, "STRATEGY_DISAGREEMENT", f"Directional consensus {ratio:.0%} is below required {self.minimum_consensus_ratio:.0%}", evaluated_at)
                for item in items
            ]
        return [
            self.evaluate(item, existing_position_quantity=existing_position_quantity, now=evaluated_at)
            if item.action == winning_action
            else self._decision(item, DecisionStatus.SUPPRESSED, "MINORITY_DIRECTION", f"Consensus selected {winning_action.value}", evaluated_at)
            for item in items
        ]

    def _decision(
        self,
        signal: StrategySignal,
        status: DecisionStatus,
        reason_code: str,
        explanation: str,
        evaluated_at: datetime,
        *,
        risk_decision: RiskDecision | None = None,
        order_request: OrderRequest | None = None,
    ) -> DecisionEvidence:
        evidence = DecisionEvidence(
            signal_id=signal.signal_id,
            status=status,
            reason_code=reason_code,
            explanation=explanation,
            evaluated_at=evaluated_at,
            confidence=signal.confidence,
            minimum_confidence=self.minimum_confidence,
            fingerprint=signal.fingerprint(),
            risk_decision=risk_decision,
            order_request=order_request,
        )
        if self.decision_journal is not None:
            self.decision_journal.record_decision(signal, evidence)
        return evidence
