"""Event driven communication layer for Agent-W-Trader.

Agents publish and subscribe to market events through this lightweight bus.
"""

class EventBus:
    def __init__(self):
        self.listeners = {}

    def subscribe(self, event_name, callback):
        self.listeners.setdefault(event_name, []).append(callback)

    def publish(self, event_name, payload=None):
        for callback in self.listeners.get(event_name, []):
            callback(payload)
