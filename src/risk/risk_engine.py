"""Deterministic pre-trade risk controls.

The risk engine is deliberately independent from AI/LLM output. Every order must
pass these checks before it can be submitted to a broker adapter.
"""

from dataclasses import dataclass

from domain.models import OrderRequest, RiskDecision


@dataclass(frozen=True)
class RiskLimits:
    max_trade_risk_percent: float = 1.0
    max_daily_loss_percent: float = 2.0
    max_order_value: float = 500_000.0

    def __post_init__(self) -> None:
        if not 0 < self.max_trade_risk_percent <= 100:
            raise ValueError("max_trade_risk_percent must be between 0 and 100")
        if not 0 < self.max_daily_loss_percent <= 100:
            raise ValueError("max_daily_loss_percent must be between 0 and 100")
        if self.max_order_value <= 0:
            raise ValueError("max_order_value must be positive")


class RiskEngine:
    def __init__(self, account_equity: float, limits: RiskLimits | None = None):
        if account_equity <= 0:
            raise ValueError("account_equity must be positive")
        self.account_equity = float(account_equity)
        self.limits = limits or RiskLimits()
        self.realized_pnl_today = 0.0
        self.kill_switch_active = False

    def set_realized_pnl_today(self, pnl: float) -> None:
        self.realized_pnl_today = float(pnl)

    def activate_kill_switch(self) -> None:
        self.kill_switch_active = True

    def deactivate_kill_switch(self) -> None:
        self.kill_switch_active = False

    def evaluate(self, request: OrderRequest) -> RiskDecision:
        max_trade_risk = self.account_equity * (
            self.limits.max_trade_risk_percent / 100
        )

        if self.kill_switch_active:
            return RiskDecision(
                approved=False,
                reason="Emergency kill switch is active",
                estimated_risk_amount=0,
                max_allowed_risk_amount=max_trade_risk,
            )

        max_daily_loss = self.account_equity * (
            self.limits.max_daily_loss_percent / 100
        )
        if self.realized_pnl_today <= -max_daily_loss:
            return RiskDecision(
                approved=False,
                reason="Maximum daily loss limit reached",
                estimated_risk_amount=0,
                max_allowed_risk_amount=max_trade_risk,
            )

        order_value = request.reference_price * request.quantity
        if order_value > self.limits.max_order_value:
            return RiskDecision(
                approved=False,
                reason="Order value exceeds configured maximum",
                estimated_risk_amount=0,
                max_allowed_risk_amount=max_trade_risk,
            )

        risk_per_unit = abs(request.reference_price - request.stop_loss_price)
        estimated_risk = risk_per_unit * request.quantity
        if risk_per_unit == 0:
            return RiskDecision(
                approved=False,
                reason="Stop-loss distance must be greater than zero",
                estimated_risk_amount=estimated_risk,
                max_allowed_risk_amount=max_trade_risk,
            )

        if estimated_risk > max_trade_risk:
            return RiskDecision(
                approved=False,
                reason="Trade risk exceeds configured account-risk limit",
                estimated_risk_amount=estimated_risk,
                max_allowed_risk_amount=max_trade_risk,
            )

        return RiskDecision(
            approved=True,
            reason="Pre-trade risk checks passed",
            estimated_risk_amount=estimated_risk,
            max_allowed_risk_amount=max_trade_risk,
        )
