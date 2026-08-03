"""Broker adapter interface for Agent-W-Trader.

Provides a standard layer for compliant broker integrations.
"""

class BrokerAdapter:
    def connect(self):
        raise NotImplementedError

    def place_order(self, order):
        raise NotImplementedError

    def get_positions(self):
        raise NotImplementedError
