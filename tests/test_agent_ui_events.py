import asyncio
import json
from types import SimpleNamespace

import pytest

from jarvis.agent.core import Agent
from jarvis.tools.base import Tool
from jarvis.tools.registry import ToolRegistry
from jarvis.ui.hub import UIHub


def _drain(queue: "asyncio.Queue[str]") -> list[dict]:
    events = []
    while not queue.empty():
        events.append(json.loads(queue.get_nowait()))
    return events


class FakeMessages:
    def __init__(self, responses: list) -> None:
        self._responses = list(responses)

    async def create(self, **kwargs: object) -> object:
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses: list) -> None:
        self.messages = FakeMessages(responses)


class FakeBlock(SimpleNamespace):
    """Ahmt die model_dump()-Schnittstelle echter Anthropic-Content-Blocks nach."""

    def model_dump(self) -> dict:
        return dict(self.__dict__)


def _text_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason="end_turn", content=[FakeBlock(type="text", text=text)]
    )


def _tool_use_response(call_id: str, name: str, tool_input: dict) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[FakeBlock(type="tool_use", id=call_id, name=name, input=tool_input)],
    )


@pytest.mark.asyncio
async def test_agent_emits_status_and_message_events() -> None:
    hub = UIHub()
    queue = hub.subscribe()
    client = FakeClient([_text_response("Hallo!")])
    agent = Agent(client=client, model="fake-model", tools=ToolRegistry(), ui_hub=hub)

    reply = await agent.handle_turn("Hi")

    assert reply == "Hallo!"
    assert _drain(queue) == [
        {"type": "user_message", "payload": {"text": "Hi"}},
        {"type": "status", "payload": {"state": "thinking"}},
        {"type": "assistant_message", "payload": {"text": "Hallo!"}},
        {"type": "status", "payload": {"state": "idle"}},
    ]


@pytest.mark.asyncio
async def test_agent_emits_tool_call_event_with_name_and_input() -> None:
    hub = UIHub()
    queue = hub.subscribe()

    async def _handler(value: str) -> str:
        return f"ok:{value}"

    registry = ToolRegistry()
    registry.register(
        Tool(
            name="echo",
            description="echo",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
            },
            handler=_handler,
        )
    )

    client = FakeClient(
        [_tool_use_response("call-1", "echo", {"value": "x"}), _text_response("fertig")]
    )
    agent = Agent(client=client, model="fake-model", tools=registry, ui_hub=hub)

    reply = await agent.handle_turn("mach echo")

    assert reply == "fertig"
    events = _drain(queue)
    assert [event["type"] for event in events] == [
        "user_message",
        "status",
        "tool_call",
        "assistant_message",
        "status",
    ]
    assert events[2]["payload"] == {"name": "echo", "input": {"value": "x"}}


@pytest.mark.asyncio
async def test_agent_without_ui_hub_does_not_error() -> None:
    client = FakeClient([_text_response("ok")])
    agent = Agent(client=client, model="fake-model", tools=ToolRegistry())

    reply = await agent.handle_turn("Hi")

    assert reply == "ok"
