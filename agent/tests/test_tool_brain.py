from pathlib import Path

import pytest

from jarvis.brain import BrainStore
from jarvis.tools.brain import brain_tools


def _tools(brain: BrainStore) -> dict[str, object]:
    return {tool.name: tool for tool in brain_tools(brain)}


def test_brain_tools_schema() -> None:
    tools = _tools(BrainStore(Path("data/brain")))

    save_schema = tools["save_to_brain"].to_anthropic_schema()
    assert set(save_schema["input_schema"]["required"]) == {"title", "content"}
    assert save_schema["input_schema"]["properties"]["category"]["enum"] == [
        "inbox",
        "projects",
        "areas",
        "resources",
    ]

    search_schema = tools["search_brain"].to_anthropic_schema()
    assert search_schema["input_schema"]["required"] == ["query"]


@pytest.mark.asyncio
async def test_save_to_brain_writes_note_and_reports_path(tmp_path: Path) -> None:
    tools = _tools(BrainStore(tmp_path))

    result = await tools["save_to_brain"].handler(
        title="Serverwartung", content="Montags um 9 Uhr.", category="projects"
    )

    note_path = tmp_path / "10-Projects" / "Serverwartung.md"
    assert note_path.is_file()
    assert str(note_path) in result


@pytest.mark.asyncio
async def test_save_to_brain_defaults_category_to_inbox(tmp_path: Path) -> None:
    tools = _tools(BrainStore(tmp_path))

    await tools["save_to_brain"].handler(title="Idee", content="Kurzer Einfall")

    assert (tmp_path / "00-Inbox" / "Idee.md").is_file()


@pytest.mark.asyncio
async def test_search_brain_returns_formatted_matches(tmp_path: Path) -> None:
    brain = BrainStore(tmp_path)
    await brain.capture("Serverwartung", "Der Server laeuft auf Port 8080.")
    tools = _tools(brain)

    result = await tools["search_brain"].handler(query="Server")

    assert "Serverwartung" in result
    assert "8080" in result


@pytest.mark.asyncio
async def test_search_brain_reports_no_matches(tmp_path: Path) -> None:
    tools = _tools(BrainStore(tmp_path))

    result = await tools["search_brain"].handler(query="nichts vorhanden")

    assert result == "Keine Treffer im Gehirn."
