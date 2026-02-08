"""
EventBus — Lightweight observer / pub-sub for decoupled communication.

Usage:
    bus = EventBus()
    bus.subscribe("building_complete", my_callback)
    bus.emit("building_complete", building_id="carrot_farm", level=2)
"""


class EventBus:
    def __init__(self):
        self._listeners: dict[str, list] = {}

    def subscribe(self, event_type: str, callback):
        self._listeners.setdefault(event_type, []).append(callback)

    def unsubscribe(self, event_type: str, callback):
        listeners = self._listeners.get(event_type, [])
        if callback in listeners:
            listeners.remove(callback)

    def emit(self, event_type: str, **data):
        for cb in self._listeners.get(event_type, []):
            cb(**data)
