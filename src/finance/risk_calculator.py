"""
Risk management engine foundation.
"""

class RiskCalculator:
    def calculate_risk(self, capital, risk_percent, stop_loss_distance):
        risk_amount = capital * (risk_percent / 100)
        return {
            "risk_amount": risk_amount,
            "stop_loss_distance": stop_loss_distance
        }
