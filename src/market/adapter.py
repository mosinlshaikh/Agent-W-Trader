"""Market-data adapter contracts and in-memory test implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict

from market.data_guard import MarketSnapshot


class MarketDataAdapter(ABC):
    """Standard contract for live or simulated market-data providers."""

    @abstractmethod
    def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        raise NotImplementedError


class InMemoryMarketDataAdapter(MarketDataAdapter):
    """Deterministic adapter for tests and paper-trading development."""

    def __init__(self) -> None:
        self._connected = False
        self._snapshots: Dict[str, MarketSnapshot] = {}

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def publish(self, symbol: str, price: float, timestamp: datetime | None = None) -> None:
        if not self._connected:
            raise RuntimeError("market-data adapter is disconnected")
        normalized = symbol.strip().upper()
        self._snapshots[normalized] = MarketSnapshot(
            symbol=normalized,
            price=price,
            timestamp=timestamp or datetime.now(timezone.utc),
        )

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        if not self._connected:
            raise RuntimeError("market-data adapter is disconnected")
        normalized = symbol.strip().upper()
        try:
            return self._snapshots[normalized]
        except KeyError as exc:
            raise KeyError(f"no market snapshot available for {normalized}") from exc
