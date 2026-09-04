from pathlib import Path

import pytest

from jarvis.brain import BrainStore


@pytest.mark.asyncio
async def test_capture_writes_frontmatter_and_content(tmp_path: Path) -> None:
    brain = BrainStore(tmp_path)

    path = await brain.capture("Projekt Alpha", "Erste Notiz", category="projects")

    assert path.parent.name == "10-Projects"
    text = path.read_text(encoding="utf-8")
    assert "title: Projekt Alpha" in text
    assert "# Projekt Alpha" in text
    assert "Erste Notiz" in text


@pytest.mark.asyncio
async def test_capture_defaults_to_inbox(tmp_path: Path) -> None:
    brain = BrainStore(tmp_path)

    path = await brain.capture("Idee", "Inhalt")

    assert path.parent.name == "00-Inbox"


@pytest.mark.asyncio
async def test_log_turn_creates_then_appends_daily_note(tmp_path: Path) -> None:
    brain = BrainStore(tmp_path)

    first = await brain.log_turn("Wie spaet ist es?", "Es ist 10 Uhr.")
    second = await brain.log_turn("Danke", "Gern geschehen.")

    assert first == second
    text = first.read_text(encoding="utf-8")
    assert "Wie spaet ist es?" in text
    assert "Danke" in text


@pytest.mark.asyncio
async def test_search_finds_matching_note_ranked_by_keyword_count(
    tmp_path: Path,
) -> None:
    brain = BrainStore(tmp_path)
    await brain.capture("Python Tipps", "Python ist grossartig. Python, Python!")
    await brain.capture("Kochrezept", "Nudeln mit Tomatensauce")

    results = await brain.search("Python")

    assert len(results) == 1
    assert results[0].title == "Python Tipps"


@pytest.mark.asyncio
async def test_search_returns_empty_list_when_vault_missing(tmp_path: Path) -> None:
    brain = BrainStore(tmp_path / "does-not-exist")

    assert await brain.search("irgendwas") == []


@pytest.mark.asyncio
async def test_search_ignores_short_stopword_like_query(tmp_path: Path) -> None:
    brain = BrainStore(tmp_path)
    await brain.capture("Notiz", "Inhalt")

    assert await brain.search("zu") == []


@pytest.mark.asyncio
async def test_context_block_empty_when_no_matches(tmp_path: Path) -> None:
    brain = BrainStore(tmp_path)

    assert await brain.context_block("nichts vorhanden") == ""


@pytest.mark.asyncio
async def test_context_block_contains_titles_and_respects_max_chars(
    tmp_path: Path,
) -> None:
    brain = BrainStore(tmp_path)
    await brain.capture("Serverwartung", "Der Server wird jeden Montag gewartet.")

    block = await brain.context_block("Server", max_chars=1200)

    assert "Serverwartung" in block
    assert block.startswith("## Relevanter Kontext aus dem Gehirn")

    tiny_block = await brain.context_block("Server", max_chars=1)
    assert tiny_block == ""
