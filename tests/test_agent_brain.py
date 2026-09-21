from datetime import datetime,timezone
import pytest
from agent_brain.contracts import AgentAction,AgentProposal
from agent_brain.firewall import EvidenceFirewall,EvidenceFirewallRejected
from agent_brain.supervisor import SupervisorAgent
from market_domains.models import EvidenceStatus,MarketDomain,MarketEvidence

def ev(status=EvidenceStatus.VERIFIED,domain=MarketDomain.INDIA,instrument="NIFTY"):
 return MarketEvidence(domain=domain,instrument=instrument,evidence_type="QUOTE",provider="certified",observed_at=datetime.now(timezone.utc),status=status,value={"price":25000},provenance="test")
def proposal(action=AgentAction.BUY,eids=None,domain=MarketDomain.INDIA,instrument="NIFTY",agent="trend"):
 return AgentProposal(agent_id=agent,domain=domain,instrument=instrument,action=action,confidence=.8,evidence_ids=eids or [],invalidation="price invalidates setup" if action in {AgentAction.BUY,AgentAction.SELL} else None)

def test_directional_ai_claim_without_evidence_is_blocked():
 with pytest.raises(EvidenceFirewallRejected,match="no evidence"): EvidenceFirewall().validate(proposal(),{})
def test_stale_evidence_is_blocked():
 e=ev(EvidenceStatus.STALE)
 with pytest.raises(EvidenceFirewallRejected,match="not verified"): EvidenceFirewall().validate(proposal(eids=[e.evidence_id]),{e.evidence_id:e})
def test_cross_market_evidence_is_blocked():
 e=ev(domain=MarketDomain.CRYPTO,instrument="NIFTY")
 with pytest.raises(EvidenceFirewallRejected,match="cross-domain"): EvidenceFirewall().validate(proposal(eids=[e.evidence_id]),{e.evidence_id:e})
def test_supervisor_abstains_on_buy_sell_tie():
 e=ev(); ps=[proposal(AgentAction.BUY,[e.evidence_id],agent="a"),proposal(AgentAction.SELL,[e.evidence_id],agent="b")]
 d=SupervisorAgent().decide(ps,{e.evidence_id:e}); assert d.action==AgentAction.ABSTAIN; assert not d.risk_authorized
def test_supervisor_consensus_never_grants_risk_authority():
 e=ev(); ps=[proposal(AgentAction.BUY,[e.evidence_id],agent="a"),proposal(AgentAction.BUY,[e.evidence_id],agent="b")]
 d=SupervisorAgent().decide(ps,{e.evidence_id:e}); assert d.action==AgentAction.BUY; assert d.evidence_ids==[e.evidence_id]; assert d.risk_authorized is False
