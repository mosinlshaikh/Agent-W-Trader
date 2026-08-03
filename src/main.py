"""
Agent-W-Trader Entry Point
Local Agentic AI Trading Research Engine
"""

from core.orchestrator import Orchestrator


def main():
    system = Orchestrator()
    system.start()


if __name__ == "__main__":
    main()
