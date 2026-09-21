from __future__ import annotations
from typing import Protocol
from .execution_intent import ExecutionIntent
from .reconciliation import BrokerOrderSnapshot

class BrokerUnavailable(RuntimeError):pass
class DuplicateExecutionIntent(RuntimeError):pass
class LiveMoneyDisabled(RuntimeError):pass
class ExecutionBroker(Protocol):
    def submit(self,intent:ExecutionIntent)->BrokerOrderSnapshot:...
class ExecutionGateway:
    """Idempotent broker boundary. Live money is explicitly disabled by default."""
    def __init__(self,broker:ExecutionBroker,allow_live_money:bool=False):self.broker=broker;self.allow_live_money=allow_live_money;self._submitted:set[str]=set()
    def submit(self,intent:ExecutionIntent)->BrokerOrderSnapshot:
        if intent.live_money and not self.allow_live_money:raise LiveMoneyDisabled("live-money execution disabled")
        if intent.intent_id in self._submitted:raise DuplicateExecutionIntent("duplicate execution intent")
        try:snapshot=self.broker.submit(intent)
        except Exception as exc:raise BrokerUnavailable("broker submission failed") from exc
        if snapshot.client_intent_id!=intent.intent_id:raise BrokerUnavailable("broker acknowledgement identity mismatch")
        self._submitted.add(intent.intent_id)
        return snapshot
