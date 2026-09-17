import asyncio
import datetime as dt

import pytest

from jarvis.scheduler import DailyBriefingTrigger


def test_seconds_until_next_same_day() -> None:
    now = dt.datetime(2026, 7, 29, 7, 0, 0)
    trigger = DailyBriefingTrigger(asyncio.Queue(), at=dt.time(8, 0), now=lambda: now)
    assert trigger.seconds_until_next() == pytest.approx(3600.0)


def test_seconds_until_next_rolls_over_to_tomorrow_when_time_passed() -> None:
    now = dt.datetime(2026, 7, 29, 9, 0, 0)
    trigger = DailyBriefingTrigger(asyncio.Queue(), at=dt.time(8, 0), now=lambda: now)
    expected = dt.timedelta(hours=23).total_seconds()
    assert trigger.seconds_until_next() == pytest.approx(expected)


@pytest.mark.asyncio
async def test_run_enqueues_prompt_repeatedly() -> None:
    queue: asyncio.Queue[str] = asyncio.Queue()
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        await asyncio.sleep(0)  # Kontrolle an den Event-Loop abgeben

    fixed_now = dt.datetime(2026, 7, 29, 7, 0, 0)
    trigger = DailyBriefingTrigger(
        queue,
        at=dt.time(8, 0),
        prompt="Briefing!",
        now=lambda: fixed_now,
        sleep=fake_sleep,
    )

    task = asyncio.create_task(trigger.run())
    for _ in range(200):
        if queue.qsize() >= 3:
            break
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert queue.qsize() >= 3
    assert queue.get_nowait() == "Briefing!"
    assert len(sleep_calls) >= 3
    assert all(s == pytest.approx(3600.0) for s in sleep_calls)
