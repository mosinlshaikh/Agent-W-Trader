"""Paper trading simulator foundation for Agent-W-Trader."""

class PaperTrader:
    def __init__(self, capital=100000):
        self.capital = capital
        self.positions = {}

    def execute_virtual_order(self, symbol, side, quantity, price):
        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "mode": "PAPER"
        }
