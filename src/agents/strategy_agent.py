"""Strategy generation agent foundation."""

class StrategyAgent:
    name = "StrategyAgent"

    def generate(self, market_context):
        return {"agent": self.name, "signal": "WAIT", "context": market_context}
