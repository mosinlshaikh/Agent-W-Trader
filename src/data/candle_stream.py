"""
Candle Stream Engine

Handles OHLCV candle pipeline for analysis agents.
"""

class CandleStream:
    def __init__(self):
        self.candles = []

    def add_candle(self, candle):
        self.candles.append(candle)

    def latest(self):
        return self.candles[-1] if self.candles else None
