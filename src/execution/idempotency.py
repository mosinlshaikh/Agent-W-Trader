"""Duplicate-order protection for safe execution retries."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Dict

from domain.models import OrderRequest


class DuplicateOrderError(RuntimeError):
    """Raised when an equivalent order is submitted inside the protection window."""


class IdempotencyGuard:
    def __init__(self, window_seconds: int = 30) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.window = timedelta(seconds=window_seconds)
        self._seen: Dict[str, datetime] = {}

    @staticmethod
    def fingerprint(request: OrderRequest) -> str:
        payload = request.model_dump(mode="json")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def register(self, request: OrderRequest, now: datetime | None = None) -> str:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        self._purge(current)
        key = self.fingerprint(request)
        previous = self._seen.get(key)
        if previous is not None and current - previous <= self.window:
            raise DuplicateOrderError("duplicate order blocked inside idempotency window")
        self._seen[key] = current
        return key

    def _purge(self, now: datetime) -> None:
        expired = [key for key, timestamp in self._seen.items() if now - timestamp > self.window]
        for key in expired:
            del self._seen[key]
