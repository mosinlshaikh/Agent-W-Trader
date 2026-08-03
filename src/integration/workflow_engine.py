"""Workflow engine foundation.
Controls data -> agents -> decision -> execution flow.
"""


class WorkflowEngine:
    def __init__(self):
        self.steps = []

    def register_step(self, step):
        self.steps.append(step)

    def run(self, context=None):
        results = []
        for step in self.steps:
            results.append(step(context))
        return results
