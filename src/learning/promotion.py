from __future__ import annotations
from enum import Enum
from pydantic import BaseModel,Field

class PromotionStatus(str,Enum): CANDIDATE="CANDIDATE"; BLOCKED="BLOCKED"; READY_FOR_HUMAN_REVIEW="READY_FOR_HUMAN_REVIEW"
class CandidateChange(BaseModel):
    candidate_id:str
    strategy_id:str
    description:str
    changes_risk_limits:bool=False
    changes_execution_code:bool=False
    backtest_passed:bool=False
    walk_forward_passed:bool=False
    paper_validation_passed:bool=False
    evidence_refs:list[str]=Field(default_factory=list)
class PromotionDecision(BaseModel):
    status:PromotionStatus; reasons:list[str]; production_applied:bool=False
class PromotionGate:
    """AI may propose; it cannot silently self-modify production."""
    def evaluate(self,c:CandidateChange)->PromotionDecision:
        reasons=[]
        if c.changes_risk_limits: reasons.append("risk-limit changes require explicit human approval")
        if c.changes_execution_code: reasons.append("execution-code changes require explicit human approval")
        if not c.evidence_refs: reasons.append("learning candidate has no evidence references")
        if not c.backtest_passed: reasons.append("backtest not passed")
        if not c.walk_forward_passed: reasons.append("walk-forward not passed")
        if not c.paper_validation_passed: reasons.append("paper validation not passed")
        hard_validation=[r for r in reasons if "not passed" in r or "no evidence" in r]
        status=PromotionStatus.BLOCKED if hard_validation else PromotionStatus.READY_FOR_HUMAN_REVIEW
        return PromotionDecision(status=status,reasons=reasons,production_applied=False)
