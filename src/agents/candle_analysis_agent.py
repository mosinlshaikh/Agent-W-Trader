"""Candle analysis worker foundation."""

class CandleAnalysisAgent:
    name = "CandleAnalysisAgent"

    def analyze(self, candles):
        return {"agent": self.name, "patterns": [], "candles": candles}
