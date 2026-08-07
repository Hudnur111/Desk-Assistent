import asyncio
import json
import logging

import pytest

from jarvis.resource_monitor import log_resource_usage_periodically
from jarvis.ui.hub import UIHub


@pytest.mark.asyncio
async def test_logs_resource_usage_periodically(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="jarvis.resource_monitor")

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            log_resource_usage_periodically(interval_seconds=0.01), timeout=0.05
        )

    assert "Ressourcen" in caplog.text
    assert "max_rss" in caplog.text


@pytest.mark.asyncio
async def test_emits_resource_event_when_ui_hub_given() -> None:
    hub = UIHub()
    queue = hub.subscribe()

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            log_resource_usage_periodically(interval_seconds=0.01, ui_hub=hub),
            timeout=0.05,
        )

    event = json.loads(queue.get_nowait())
    assert event["type"] == "resource"
    assert isinstance(event["payload"]["rss_mb"], (int, float))
