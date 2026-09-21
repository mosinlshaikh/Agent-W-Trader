from __future__ import annotations
from enum import Enum
from pydantic import BaseModel,Field
from market_domains.models import MarketDomain

class AgentAction(str,Enum): BUY="BUY"; SELL="SELL"; HOLD="HOLD"; ABSTAIN="ABSTAIN"
class AgentProposal(BaseModel):
    agent_id:str
    domain:MarketDomain
    instrument:str
    action:AgentAction
    confidence:float=Field(ge=0,le=1)
    evidence_ids:list[str]=Field(default_factory=list)
    claims:list[str]=Field(default_factory=list)
    invalidation:str|None=None
    reasoning_summary:str=""
class GroundedDecision(BaseModel):
    domain:MarketDomain
    instrument:str
    action:AgentAction
    confidence:float=Field(ge=0,le=1)
    accepted_agent_ids:list[str]
    evidence_ids:list[str]
    reason:str
    risk_authorized:bool=False
