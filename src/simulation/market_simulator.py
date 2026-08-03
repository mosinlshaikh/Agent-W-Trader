"""Local market simulator for paper trading tests."""


class MarketSimulator:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True
        return "simulation_started"

    def stop(self):
        self.running = False
        return "simulation_stopped"
