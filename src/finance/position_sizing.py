"""
Position sizing engine foundation.
"""

class PositionSizer:
    def calculate(self, capital, risk_amount, stop_loss_points):
        if stop_loss_points <= 0:
            return 0
        return risk_amount / stop_loss_points
