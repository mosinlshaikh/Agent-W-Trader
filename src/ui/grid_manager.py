"""
Dynamic grid manager for multiple trading screens.
"""


class GridManager:
    def __init__(self, rows=4, columns=4):
        self.rows = rows
        self.columns = columns
        self.tiles = []

    def add_trade_tile(self, trade_id):
        self.tiles.append(trade_id)

    def get_layout(self):
        return f"{self.rows}x{self.columns}"
