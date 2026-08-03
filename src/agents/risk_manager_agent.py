"""Risk management agent foundation."""

class RiskManagerAgent:
    name = "RiskManagerAgent"

    def validate(self, trade):
        return {"agent": self.name, "approved": False, "trade": trade}
