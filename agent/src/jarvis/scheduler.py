import asyncio
import datetime as dt
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

DEFAULT_BRIEFING_PROMPT = (
    "Gib mir eine kurze Tagesuebersicht: aktuelles Datum, offene Punkte "
    "aus fruehreren Notizen (falls vorhanden) und was ich heute im Blick "
    "behalten sollte."
)


class DailyBriefingTrigger:
    """Legt zu einer festen Uhrzeit taeglich einen Prompt in die Agent-Queue.

    Uhrzeit-Quelle und Sleep-Funktion sind injizierbar, damit die
    Zeitlogik ohne echtes Warten getestet werden kann.
    """

    def __init__(
        self,
        output_queue: "asyncio.Queue[str]",
        at: dt.time,
        prompt: str = DEFAULT_BRIEFING_PROMPT,
        now: Callable[[], dt.datetime] = dt.datetime.now,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._queue = output_queue
        self._at = at
        self._prompt = prompt
        self._now = now
        self._sleep = sleep

    def seconds_until_next(self) -> float:
        now = self._now()
        target = now.replace(
            hour=self._at.hour, minute=self._at.minute, second=0, microsecond=0
        )
        if target <= now:
            target += dt.timedelta(days=1)
        return (target - now).total_seconds()

    async def run(self) -> None:
        while True:
            delay = self.seconds_until_next()
            logger.info("Naechstes Tages-Briefing in %.0f Sekunden", delay)
            await self._sleep(delay)
            await self._queue.put(self._prompt)
