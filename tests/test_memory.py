from pathlib import Path

import pytest

from jarvis.memory import MemoryStore


@pytest.mark.asyncio
async def test_load_returns_empty_list_when_no_file_exists(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "history.json")
    assert await store.load() == []


@pytest.mark.asyncio
async def test_save_then_load_round_trips(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "nested" / "history.json")
    history = [
        {"role": "user", "content": "Hallo"},
        {"role": "assistant", "content": [{"type": "text", "text": "Hi!"}]},
    ]

    await store.save(history)
    loaded = await store.load()

    assert loaded == history


@pytest.mark.asyncio
async def test_save_overwrites_previous_content(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "history.json")

    await store.save([{"role": "user", "content": "erste"}])
    await store.save([{"role": "user", "content": "zweite"}])

    assert await store.load() == [{"role": "user", "content": "zweite"}]
