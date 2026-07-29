import asyncio
import logging
import resource

logger = logging.getLogger(__name__)


async def log_resource_usage_periodically(interval_seconds: float = 300.0) -> None:
    while True:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        logger.info(
            "Ressourcen: max_rss=%.1fMB user_cpu=%.1fs system_cpu=%.1fs",
            usage.ru_maxrss / 1024,
            usage.ru_utime,
            usage.ru_stime,
        )
        await asyncio.sleep(interval_seconds)
