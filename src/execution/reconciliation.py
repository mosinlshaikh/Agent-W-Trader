from __future__ import annotations
from enum import Enum
from pydantic import BaseModel,Field
from .execution_intent import ExecutionIntent

class BrokerOrderState(str,Enum): ACKNOWLEDGED="ACKNOWLEDGED"; PARTIAL="PARTIAL"; FILLED="FILLED"; REJECTED="REJECTED"; CANCELLED="CANCELLED"; UNKNOWN="UNKNOWN"
class BrokerOrderSnapshot(BaseModel):
    broker_order_id:str; client_intent_id:str; state:BrokerOrderState; filled_quantity:float=Field(ge=0); average_fill_price:float|None=Field(default=None,gt=0)
class ReconciliationState(str,Enum): MATCHED="MATCHED"; PENDING="PENDING"; BLOCKED="BLOCKED"
class ReconciliationResult(BaseModel): state:ReconciliationState; reasons:list[str]
class ExecutionReconciler:
    def reconcile(self,intent:ExecutionIntent,snapshot:BrokerOrderSnapshot)->ReconciliationResult:
        reasons=[]
        if snapshot.client_intent_id!=intent.intent_id: reasons.append("broker/client intent mismatch")
        if snapshot.filled_quantity>intent.quantity: reasons.append("broker overfill detected")
        if snapshot.state==BrokerOrderState.UNKNOWN: reasons.append("unknown broker order state")
        if snapshot.state==BrokerOrderState.FILLED and snapshot.filled_quantity!=intent.quantity: reasons.append("filled state quantity mismatch")
        if reasons:return ReconciliationResult(state=ReconciliationState.BLOCKED,reasons=reasons)
        if snapshot.state in {BrokerOrderState.ACKNOWLEDGED,BrokerOrderState.PARTIAL}:return ReconciliationResult(state=ReconciliationState.PENDING,reasons=["awaiting final broker state"])
        return ReconciliationResult(state=ReconciliationState.MATCHED,reasons=[])
