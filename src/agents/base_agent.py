"""
Base AI Worker Agent
All trading agents inherit this class.
"""


class BaseAgent:
    name = "BaseAgent"

    def initialize(self):
        print(f"{self.name} initialized")

    def analyze(self, data):
        raise NotImplementedError

    def learn(self, result):
        pass
