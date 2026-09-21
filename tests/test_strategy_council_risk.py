from datetime import datetime,timezone
from agent_brain.contracts import AgentAction,AgentProposal,GroundedDecision
from market_domains.models import EvidenceStatus,MarketDomain,MarketEvidence
from strategy_council.council import StrategyCouncil
from strategy_council.risk_authorizer import AdvancedRiskAuthorizer,RiskLimits,RiskRequest,RiskVerdict

def evidence(): return MarketEvidence(domain=MarketDomain.INDIA,instrument="NIFTY",evidence_type="QUOTE",provider="test",observed_at=datetime.now(timezone.utc),status=EvidenceStatus.VERIFIED,value=25000,provenance="test")
def prop(agent,eid): return AgentProposal(agent_id=agent,domain=MarketDomain.INDIA,instrument="NIFTY",action=AgentAction.BUY,confidence=.8,evidence_ids=[eid],invalidation="stop invalidation")
def decision(): return GroundedDecision(domain=MarketDomain.INDIA,instrument="NIFTY",action=AgentAction.BUY,confidence=.8,accepted_agent_ids=["a","b"],evidence_ids=["e"],reason="grounded",risk_authorized=False)
def request(**kw):
 d=dict(domain=MarketDomain.INDIA,instrument="NIFTY",account_equity=100000,order_value=20000,stop_loss_amount=500,daily_pnl=0,current_gross_exposure=10000,leverage=1,kill_switch=False);d.update(kw);return RiskRequest(**d)

def test_council_requires_multiple_agent_roles():
 e=evidence(); ps=[prop("trend",e.evidence_id),prop("news",e.evidence_id)]; out=StrategyCouncil().deliberate(ps,{e.evidence_id:e},{"trend":"trend","news":"news"}); assert out.quorum_met; assert out.decision.action==AgentAction.BUY

def test_same_role_does_not_form_diverse_quorum():
 e=evidence();ps=[prop("a",e.evidence_id),prop("b",e.evidence_id)];out=StrategyCouncil().deliberate(ps,{e.evidence_id:e},{"a":"trend","b":"trend"});assert not out.quorum_met;assert out.decision.action==AgentAction.ABSTAIN

def test_risk_approves_only_within_limits(): assert AdvancedRiskAuthorizer().authorize(decision(),request(),RiskLimits()).verdict==RiskVerdict.APPROVED

def test_kill_switch_is_final(): assert AdvancedRiskAuthorizer().authorize(decision(),request(kill_switch=True),RiskLimits()).verdict==RiskVerdict.REJECTED

def test_ai_confidence_cannot_override_trade_risk():
 d=decision().model_copy(update={"confidence":1.0}); out=AdvancedRiskAuthorizer().authorize(d,request(stop_loss_amount=5000),RiskLimits(max_trade_risk_pct=1)); assert out.verdict==RiskVerdict.REJECTED

def test_daily_loss_and_exposure_fail_closed():
 out=AdvancedRiskAuthorizer().authorize(decision(),request(daily_pnl=-3000,current_gross_exposure=95000),RiskLimits()); assert out.verdict==RiskVerdict.REJECTED; assert len(out.reasons)>=2
