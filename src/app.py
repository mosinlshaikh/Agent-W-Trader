"""Agent-W-Trader application entry point."""

from integration.system_controller import SystemController


def run():
    controller = SystemController()
    controller.start()


if __name__ == "__main__":
    run()
