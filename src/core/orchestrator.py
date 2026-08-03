"""
Master Orchestrator
Coordinates all AI trading workers.
"""


class Orchestrator:
    def __init__(self):
        self.agents = []
        self.running = False

    def register_agent(self, agent):
        self.agents.append(agent)

    def start(self):
        self.running = True
        print("Agent-W-Trader Orchestrator Started")

        for agent in self.agents:
            agent.initialize()

    def stop(self):
        self.running = False
