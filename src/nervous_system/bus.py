from __future__ import annotations
from collections import defaultdict
from collections.abc import Callable
from market_domains.models import EvidenceStatus, MarketDomain
from .events import EventKind, NervousSystemEvent

class NervousSystemRejected(RuntimeError):
    pass

Handler = Callable[[NervousSystemEvent], None]

class NervousSystemBus:
    """Synchronous deterministic event bus foundation.

    Production transports may become asynchronous, but validation happens
    before dispatch and unverifiable evidence always fails closed.
    """
    def __init__(self) -> None:
        self._handlers: dict[tuple[MarketDomain, EventKind], list[Handler]] = defaultdict(list)

    def subscribe(self, domain: MarketDomain, kind: EventKind, handler: Handler) -> None:
        self._handlers[(domain, kind)].append(handler)

    def publish(self, event: NervousSystemEvent) -> int:
        if event.evidence.status != EvidenceStatus.VERIFIED:
            raise NervousSystemRejected(f"evidence not executable: {event.evidence.status.value}")
        handlers = tuple(self._handlers.get((event.domain, event.kind), ()))
        for handler in handlers:
            handler(event)
        return len(handlers)
