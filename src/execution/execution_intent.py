from __future__ import annotations
from enum import Enum
from pydantic import BaseModel,Field
from market_domains.models import MarketDomain

class ExecutionSide(str,Enum): BUY="BUY"; SELL="SELL"
class ExecutionIntent(BaseModel):
    intent_id:str; decision_id:str; domain:MarketDomain; instrument:str; side:ExecutionSide
    quantity:float=Field(gt=0); expected_price:float=Field(gt=0); risk_authorization_id:str
    evidence_ids:list[str]=Field(min_length=1); live_money:bool=False
