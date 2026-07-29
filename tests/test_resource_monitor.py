import asyncio
import logging

import pytest

from jarvis.resource_monitor import log_resource_usage_periodically


@pytest.mark.asyncio
async def test_logs_resource_usage_periodically(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="jarvis.resource_monitor")

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            log_resource_usage_periodically(interval_seconds=0.01), timeout=0.05
        )

    assert "Ressourcen" in caplog.text
    assert "max_rss" in caplog.text
