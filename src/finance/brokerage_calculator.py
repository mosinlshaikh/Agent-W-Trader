"""
Brokerage calculator foundation for Indian trading segments.
"""

class BrokerageCalculator:
    def calculate(self, orders=1, rate=20):
        return min(orders * rate, orders * rate)
