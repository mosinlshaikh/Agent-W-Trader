from __future__ import annotations
from collections import defaultdict
from pydantic import BaseModel
from agent_brain.contracts import AgentAction,AgentProposal,GroundedDecision
from agent_brain.supervisor import SupervisorAgent
from market_domains.models import MarketEvidence

class StrategyCouncilDecision(BaseModel):
    decision: GroundedDecision
    participating_roles:list[str]
    quorum_met:bool

class StrategyCouncil:
    def __init__(self,min_directional_agents:int=2): self.min_directional_agents=min_directional_agents
    def deliberate(self,proposals:list[AgentProposal],evidence:dict[str,MarketEvidence],roles:dict[str,str])->StrategyCouncilDecision:
        grounded=SupervisorAgent().decide(proposals,evidence)
        winners=[p for p in proposals if p.agent_id in grounded.accepted_agent_ids and p.action in {AgentAction.BUY,AgentAction.SELL}]
        unique_roles=sorted({roles.get(p.agent_id,"unknown") for p in winners})
        quorum=len(winners)>=self.min_directional_agents and len(unique_roles)>=2
        if not quorum and grounded.action in {AgentAction.BUY,AgentAction.SELL}:
            grounded=grounded.model_copy(update={"action":AgentAction.ABSTAIN,"confidence":0.0,"reason":"strategy council quorum not met","risk_authorized":False})
        return StrategyCouncilDecision(decision=grounded,participating_roles=unique_roles,quorum_met=quorum)
