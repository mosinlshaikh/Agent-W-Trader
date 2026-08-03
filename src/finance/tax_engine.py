"""
Indian Market Tax & Cost Engine
Calculates estimated trading costs for validation before execution.
"""

class TaxEngine:
    def calculate(self, turnover, brokerage=20, exchange_charge_rate=0.000019):
        exchange = turnover * exchange_charge_rate
        gst = (brokerage + exchange) * 0.18
        sebi = turnover * 0.000001
        total = brokerage + exchange + gst + sebi

        return {
            "brokerage": brokerage,
            "exchange_charge": exchange,
            "gst": gst,
            "sebi_charge": sebi,
            "total_cost": total
        }
