"""Agent lifecycle manager."""

class AgentManager:
    def __init__(self):
        self.agents = []

    def register(self, agent):
        self.agents.append(agent)

    def run_cycle(self, market_data=None):
        results = []
        for agent in self.agents:
            results.append(agent.analyze(market_data))
        return results
