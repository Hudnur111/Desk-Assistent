import json

import pytest

from jarvis.ui.hub import UIHub


@pytest.mark.asyncio
async def test_emit_without_subscribers_is_a_noop() -> None:
    hub = UIHub()
    await hub.emit("status", state="idle")


@pytest.mark.asyncio
async def test_emit_delivers_to_all_subscribers() -> None:
    hub = UIHub()
    queue_a = hub.subscribe()
    queue_b = hub.subscribe()

    await hub.emit("status", state="listening")

    message_a = json.loads(queue_a.get_nowait())
    message_b = json.loads(queue_b.get_nowait())
    assert message_a == {"type": "status", "payload": {"state": "listening"}}
    assert message_b == message_a


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery() -> None:
    hub = UIHub()
    queue = hub.subscribe()
    hub.unsubscribe(queue)

    await hub.emit("status", state="idle")

    assert queue.qsize() == 0
