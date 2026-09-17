import anthropic
import httpx
import pytest

from jarvis.agent.core import API_ERROR_REPLY, Agent
from jarvis.tools.registry import ToolRegistry


class FailingMessages:
    async def create(self, **kwargs: object) -> object:
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        raise anthropic.APIConnectionError(message="boom", request=request)


class FailingClient:
    def __init__(self) -> None:
        self.messages = FailingMessages()


@pytest.mark.asyncio
async def test_handle_turn_returns_fallback_on_api_error() -> None:
    agent = Agent(client=FailingClient(), model="fake-model", tools=ToolRegistry())

    reply = await agent.handle_turn("Hallo")

    assert reply == API_ERROR_REPLY


@pytest.mark.asyncio
async def test_history_is_rolled_back_after_api_error() -> None:
    agent = Agent(client=FailingClient(), model="fake-model", tools=ToolRegistry())

    await agent.handle_turn("erste Frage")

    # Keine verwaiste User-Nachricht im Verlauf, sonst verletzt der naechste
    # Aufruf die von der API geforderte User/Assistant-Rollenalternation.
    assert agent._history == []
