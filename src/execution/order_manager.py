"""
Real Order Management System Foundation

Responsible for:
- Order lifecycle
- Order validation
- Execution workflow
- Broker adapter communication
"""

class OrderManager:
    def __init__(self):
        self.orders = []

    def create_order(self, symbol, side, quantity):
        order = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "status": "PENDING"
        }
        self.orders.append(order)
        return order
