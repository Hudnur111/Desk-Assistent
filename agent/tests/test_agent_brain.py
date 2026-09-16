from pathlib import Path
from types import SimpleNamespace

import pytest

from jarvis.agent.core import Agent
from jarvis.brain import BrainStore
from jarvis.tools.registry import ToolRegistry


class FakeMessages:
    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses: list) -> None:
        self.messages = FakeMessages(responses)


class FakeBlock(SimpleNamespace):
    def model_dump(self) -> dict:
        return dict(self.__dict__)


def _text_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason="end_turn", content=[FakeBlock(type="text", text=text)]
    )


@pytest.mark.asyncio
async def test_handle_turn_logs_to_brain_after_reply(tmp_path: Path) -> None:
    brain = BrainStore(tmp_path)
    client = FakeClient([_text_response("Hallo!")])
    agent = Agent(client=client, model="fake-model", tools=ToolRegistry(), brain=brain)

    await agent.handle_turn("Hi")

    matches = await brain.search("Hallo")
    assert any("Hi" in m.snippet or "Hallo" in m.snippet for m in matches)


@pytest.mark.asyncio
async def test_handle_turn_injects_brain_context_into_system_prompt(
    tmp_path: Path,
) -> None:
    brain = BrainStore(tmp_path)
    await brain.capture("Serverwartung", "Der Server laeuft auf Port 8080.")
    client = FakeClient([_text_response("ok")])
    agent = Agent(client=client, model="fake-model", tools=ToolRegistry(), brain=brain)

    await agent.handle_turn("Was weisst du ueber den Server?")

    system_prompt = client.messages.calls[0]["system"]
    assert "Serverwartung" in system_prompt


@pytest.mark.asyncio
async def test_windowed_history_keeps_only_recent_full_turns() -> None:
    client = FakeClient([_text_response("ok")])
    agent = Agent(
        client=client,
        model="fake-model",
        tools=ToolRegistry(),
        max_context_messages=4,
    )
    agent._history = [
        {"role": "user", "content": "alt 1"},
        {"role": "assistant", "content": "antwort 1"},
        {"role": "user", "content": "alt 2"},
        {"role": "assistant", "content": "antwort 2"},
    ]

    await agent.handle_turn("neu")

    sent_messages = client.messages.calls[0]["messages"]
    assert sent_messages[0] == {"role": "user", "content": "alt 2"}
    assert sent_messages[-1] == {"role": "user", "content": "neu"}
