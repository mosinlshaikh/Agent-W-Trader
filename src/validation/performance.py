from __future__ import annotations
from math import sqrt
from pydantic import BaseModel,Field

class TradeResult(BaseModel):
    gross_pnl:float
    fees:float=Field(ge=0)
    slippage:float=Field(ge=0)
    partial_fill_ratio:float=Field(default=1,ge=0,le=1)
    @property
    def net_pnl(self)->float: return self.gross_pnl-self.fees-self.slippage

class ValidationLimits(BaseModel):
    max_drawdown_pct:float=Field(default=15,gt=0)
    min_trades:int=Field(default=30,ge=1)
    min_profit_factor:float=Field(default=1.1,gt=0)
    min_fill_ratio:float=Field(default=.8,ge=0,le=1)

class PerformanceReport(BaseModel):
    trades:int; net_pnl:float; max_drawdown_pct:float; profit_factor:float; avg_fill_ratio:float; passed:bool; reasons:list[str]

class PerformanceValidator:
    def evaluate(self,trades:list[TradeResult],starting_equity:float,limits:ValidationLimits)->PerformanceReport:
        if starting_equity<=0: raise ValueError("starting equity must be positive")
        equity=starting_equity; peak=equity; maxdd=0.0; gains=0.0; losses=0.0
        for t in trades:
            n=t.net_pnl; equity+=n; peak=max(peak,equity); maxdd=max(maxdd,(peak-equity)/peak*100 if peak else 0)
            if n>0:gains+=n
            elif n<0:losses+=abs(n)
        pf=gains/losses if losses else (float("inf") if gains else 0.0)
        fill=sum(t.partial_fill_ratio for t in trades)/len(trades) if trades else 0.0
        reasons=[]
        if len(trades)<limits.min_trades: reasons.append("insufficient trade sample")
        if maxdd>limits.max_drawdown_pct: reasons.append("maximum drawdown exceeded")
        if pf<limits.min_profit_factor: reasons.append("profit factor below threshold")
        if fill<limits.min_fill_ratio: reasons.append("fill quality below threshold")
        return PerformanceReport(trades=len(trades),net_pnl=equity-starting_equity,max_drawdown_pct=maxdd,profit_factor=pf,avg_fill_ratio=fill,passed=not reasons,reasons=reasons)
