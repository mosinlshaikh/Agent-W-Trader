import pytest
from market_domains.models import MarketDomain
from execution.execution_gateway import BrokerUnavailable,DuplicateExecutionIntent,ExecutionGateway,LiveMoneyDisabled
from execution.execution_intent import ExecutionIntent,ExecutionSide
from execution.reconciliation import BrokerOrderSnapshot,BrokerOrderState,ExecutionReconciler,ReconciliationState

def intent(**kw):
 d=dict(intent_id="i1",decision_id="d1",domain=MarketDomain.INDIA,instrument="NIFTY",side=ExecutionSide.BUY,quantity=10,expected_price=25000,risk_authorization_id="r1",evidence_ids=["e1"],live_money=False);d.update(kw);return ExecutionIntent(**d)
class Broker:
 def __init__(self,state=BrokerOrderState.ACKNOWLEDGED):self.state=state
 def submit(self,i):return BrokerOrderSnapshot(broker_order_id="b1",client_intent_id=i.intent_id,state=self.state,filled_quantity=0)
class BrokenBroker:
 def submit(self,i):raise RuntimeError("outage")

def test_duplicate_intent_cannot_submit_twice():
 g=ExecutionGateway(Broker());g.submit(intent());
 with pytest.raises(DuplicateExecutionIntent):g.submit(intent())
def test_broker_outage_fails_closed():
 with pytest.raises(BrokerUnavailable):ExecutionGateway(BrokenBroker()).submit(intent())
def test_live_money_is_disabled_by_default():
 with pytest.raises(LiveMoneyDisabled):ExecutionGateway(Broker()).submit(intent(live_money=True))
def test_partial_fill_remains_pending():
 i=intent();s=BrokerOrderSnapshot(broker_order_id="b",client_intent_id=i.intent_id,state=BrokerOrderState.PARTIAL,filled_quantity=4,average_fill_price=25001);assert ExecutionReconciler().reconcile(i,s).state==ReconciliationState.PENDING
def test_unknown_broker_state_blocks_reconciliation():
 i=intent();s=BrokerOrderSnapshot(broker_order_id="b",client_intent_id=i.intent_id,state=BrokerOrderState.UNKNOWN,filled_quantity=0);assert ExecutionReconciler().reconcile(i,s).state==ReconciliationState.BLOCKED
def test_overfill_blocks_reconciliation():
 i=intent();s=BrokerOrderSnapshot(broker_order_id="b",client_intent_id=i.intent_id,state=BrokerOrderState.FILLED,filled_quantity=11,average_fill_price=25000);assert ExecutionReconciler().reconcile(i,s).state==ReconciliationState.BLOCKED
