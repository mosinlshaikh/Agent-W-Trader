"""
Order Book Intelligence Engine
Foundation for depth, liquidity and market microstructure analysis.
"""

class OrderBookEngine:
    def __init__(self):
        self.bids = []
        self.asks = []

    def update(self, bids, asks):
        self.bids = bids
        self.asks = asks

    def imbalance(self):
        bid_volume = sum(x[1] for x in self.bids)
        ask_volume = sum(x[1] for x in self.asks)

        total = bid_volume + ask_volume
        if total == 0:
            return 0

        return (bid_volume - ask_volume) / total
