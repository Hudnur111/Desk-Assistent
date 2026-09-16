import asyncio
import json
from typing import Any


class UIHub:
    """Verteilt Zustands-Events an alle verbundenen WebSocket-Clients.

    Ist der Agent/die Voice-Pipeline nicht mit einer UI verbunden, bleibt die
    Subscriber-Menge einfach leer und emit() wird zum No-Op - Text- und
    Sprachmodus funktionieren unveraendert ohne laufende UI.
    """

    def __init__(self) -> None:
        self._subscribers: set["asyncio.Queue[str]"] = set()

    def subscribe(self) -> "asyncio.Queue[str]":
        queue: "asyncio.Queue[str]" = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: "asyncio.Queue[str]") -> None:
        self._subscribers.discard(queue)

    async def emit(self, event_type: str, **payload: Any) -> None:
        message = json.dumps({"type": event_type, "payload": payload})
        for queue in list(self._subscribers):
            queue.put_nowait(message)
