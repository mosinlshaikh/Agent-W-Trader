"""System controller for Agent-W-Trader.
Coordinates startup and lifecycle of all major modules.
"""


class SystemController:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True
        return "Agent-W-Trader system started"

    def stop(self):
        self.running = False
        return "Agent-W-Trader system stopped"
