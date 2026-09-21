from __future__ import annotations
from datetime import datetime,timezone
from pydantic import BaseModel,Field
from market_domains.models import MarketDomain

class OutcomeRecord(BaseModel):
    decision_id:str
    domain:MarketDomain
    instrument:str
    strategy_id:str
    agent_ids:list[str]
    evidence_ids:list[str]
    risk_reasons:list[str]=Field(default_factory=list)
    order_id:str|None=None
    fill_ids:list[str]=Field(default_factory=list)
    gross_pnl:float=0
    fees:float=Field(default=0,ge=0)
    slippage:float=Field(default=0,ge=0)
    recorded_at:datetime=Field(default_factory=lambda:datetime.now(timezone.utc))
    @property
    def net_pnl(self)->float:return self.gross_pnl-self.fees-self.slippage

class StrategyAttribution(BaseModel):
    strategy_id:str; observations:int; net_pnl:float; wins:int; losses:int

class LearningJournal:
    """Append-only in-memory contract; persistent adapter is added separately."""
    def __init__(self): self._records:list[OutcomeRecord]=[];self._ids:set[str]=set()
    def append(self,record:OutcomeRecord)->None:
        if record.decision_id in self._ids: raise ValueError("duplicate decision outcome")
        self._records.append(record);self._ids.add(record.decision_id)
    def records(self)->tuple[OutcomeRecord,...]:return tuple(self._records)
    def attribution(self,strategy_id:str)->StrategyAttribution:
        rows=[r for r in self._records if r.strategy_id==strategy_id]
        return StrategyAttribution(strategy_id=strategy_id,observations=len(rows),net_pnl=sum(r.net_pnl for r in rows),wins=sum(r.net_pnl>0 for r in rows),losses=sum(r.net_pnl<0 for r in rows))
