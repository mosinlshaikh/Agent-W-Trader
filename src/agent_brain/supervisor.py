from __future__ import annotations
from collections import Counter
from market_domains.models import MarketEvidence
from .contracts import AgentAction,AgentProposal,GroundedDecision
from .firewall import EvidenceFirewall,EvidenceFirewallRejected

class SupervisorAgent:
    """Aggregates grounded proposals. It never authorizes risk or broker execution."""
    def __init__(self,firewall:EvidenceFirewall|None=None): self.firewall=firewall or EvidenceFirewall()
    def decide(self,proposals:list[AgentProposal],evidence:dict[str,MarketEvidence])->GroundedDecision:
        if not proposals: raise ValueError("at least one proposal is required")
        domain=proposals[0].domain; instrument=proposals[0].instrument.strip().upper(); accepted=[]
        for p in proposals:
            if p.domain!=domain or p.instrument.strip().upper()!=instrument: continue
            try: accepted.append(self.firewall.validate(p,evidence))
            except EvidenceFirewallRejected: continue
        directional=[p for p in accepted if p.action in {AgentAction.BUY,AgentAction.SELL}]
        if not directional:
            return GroundedDecision(domain=domain,instrument=instrument,action=AgentAction.ABSTAIN,confidence=0,accepted_agent_ids=[p.agent_id for p in accepted],evidence_ids=[],reason="no grounded directional consensus",risk_authorized=False)
        counts=Counter(p.action for p in directional); top,count=counts.most_common(1)[0]
        if list(counts.values()).count(count)>1:
            return GroundedDecision(domain=domain,instrument=instrument,action=AgentAction.ABSTAIN,confidence=0,accepted_agent_ids=[p.agent_id for p in accepted],evidence_ids=[],reason="agent disagreement; abstaining",risk_authorized=False)
        winners=[p for p in directional if p.action==top]; conf=sum(p.confidence for p in winners)/len(winners)
        ids=sorted({eid for p in winners for eid in p.evidence_ids})
        return GroundedDecision(domain=domain,instrument=instrument,action=top,confidence=conf,accepted_agent_ids=[p.agent_id for p in winners],evidence_ids=ids,reason="grounded agent consensus; deterministic risk authorization still required",risk_authorized=False)
