"""System bootstrap loader."""

from core.orchestrator import Orchestrator


def initialize_system():
    return Orchestrator()
