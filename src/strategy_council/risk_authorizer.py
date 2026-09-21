from __future__ import annotations
from enum import Enum
from pydantic import BaseModel,Field
from agent_brain.contracts import AgentAction,GroundedDecision
from market_domains.models import MarketDomain

class RiskVerdict(str,Enum): APPROVED="APPROVED"; REJECTED="REJECTED"
class RiskLimits(BaseModel):
    max_trade_risk_pct:float=Field(default=1.0,gt=0,le=100)
    max_daily_loss_pct:float=Field(default=2.0,gt=0,le=100)
    max_order_value:float=Field(default=500000,gt=0)
    max_gross_exposure_pct:float=Field(default=100,gt=0)
    max_leverage:float=Field(default=1,ge=1)
class RiskRequest(BaseModel):
    domain:MarketDomain; instrument:str; account_equity:float=Field(gt=0); order_value:float=Field(gt=0)
    stop_loss_amount:float=Field(gt=0); daily_pnl:float=0; current_gross_exposure:float=Field(ge=0); leverage:float=Field(default=1,ge=1)
    kill_switch:bool=False
class RiskAuthorization(BaseModel):
    verdict:RiskVerdict; reasons:list[str]; max_permitted_risk:float; projected_exposure:float
class AdvancedRiskAuthorizer:
    """Final deterministic authorization. AI confidence never overrides these rules."""
    def authorize(self,decision:GroundedDecision,request:RiskRequest,limits:RiskLimits)->RiskAuthorization:
        reasons=[]; maxrisk=request.account_equity*limits.max_trade_risk_pct/100; projected=request.current_gross_exposure+request.order_value
        if decision.action not in {AgentAction.BUY,AgentAction.SELL}: reasons.append("no directional grounded decision")
        if decision.domain!=request.domain or decision.instrument!=request.instrument.strip().upper(): reasons.append("decision/request scope mismatch")
        if request.kill_switch: reasons.append("kill switch active")
        if request.stop_loss_amount>maxrisk: reasons.append("per-trade risk limit exceeded")
        if request.daily_pnl <= -(request.account_equity*limits.max_daily_loss_pct/100): reasons.append("daily loss limit reached")
        if request.order_value>limits.max_order_value: reasons.append("maximum order value exceeded")
        if projected>request.account_equity*limits.max_gross_exposure_pct/100: reasons.append("gross exposure limit exceeded")
        if request.leverage>limits.max_leverage: reasons.append("leverage limit exceeded")
        return RiskAuthorization(verdict=RiskVerdict.REJECTED if reasons else RiskVerdict.APPROVED,reasons=reasons,max_permitted_risk=maxrisk,projected_exposure=projected)
