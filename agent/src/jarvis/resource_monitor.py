import asyncio
import logging
import resource

from .ui.hub import UIHub

logger = logging.getLogger(__name__)


async def log_resource_usage_periodically(
    interval_seconds: float = 300.0, ui_hub: UIHub | None = None
) -> None:
    while True:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_mb = usage.ru_maxrss / 1024
        logger.info(
            "Ressourcen: max_rss=%.1fMB user_cpu=%.1fs system_cpu=%.1fs",
            rss_mb,
            usage.ru_utime,
            usage.ru_stime,
        )
        if ui_hub is not None:
            await ui_hub.emit("resource", rss_mb=round(rss_mb, 1))
        await asyncio.sleep(interval_seconds)
