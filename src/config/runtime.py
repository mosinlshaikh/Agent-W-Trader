"""Validated runtime configuration wiring for paper trading."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from risk.risk_engine import RiskLimits


class PaperBrokerSettings(BaseModel):
    slippage_bps: float = Field(default=2.0, ge=0, le=100)
    max_market_data_age_seconds: float = Field(default=5.0, gt=0, le=300)


class PersistenceSettings(BaseModel):
    sqlite_path: str = "data/agent_w_trader.db"


class RuntimeSettings(BaseModel):
    mode: str = "paper"
    account_equity: float = Field(default=100_000.0, gt=0)
    risk: RiskLimits = RiskLimits()
    paper_broker: PaperBrokerSettings = PaperBrokerSettings()
    persistence: PersistenceSettings = PersistenceSettings()


def load_runtime_settings(path: str = "config/settings.yaml") -> RuntimeSettings:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    system = raw.get("system", {})
    risk = raw.get("risk", {})
    paper = raw.get("paper_broker", {})
    persistence = raw.get("persistence", {})
    return RuntimeSettings(
        mode=system.get("mode", "paper"),
        account_equity=system.get("account_equity", 100_000.0),
        risk=RiskLimits(
            max_trade_risk_percent=risk.get("max_trade_risk_percent", 1.0),
            max_daily_loss_percent=risk.get("max_daily_loss_percent", 2.0),
            max_order_value=risk.get("max_order_value", 500_000.0),
        ),
        paper_broker=PaperBrokerSettings(**paper),
        persistence=PersistenceSettings(**persistence),
    )
