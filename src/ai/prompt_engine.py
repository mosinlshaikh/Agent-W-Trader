"""Prompt management layer for trading agents."""

class PromptEngine:
    def build_market_prompt(self, market_data):
        return f"Analyze Indian market data with risk awareness: {market_data}"
