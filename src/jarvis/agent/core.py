import asyncio
import logging

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from ..tools.registry import ToolRegistry
from ..ui.hub import UIHub

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Du bist Jarvis, ein autonomer Assistent fuer IT-Consulting und "
    "Buero-Automatisierung. Antworte praezise auf Deutsch. Nutze die "
    "verfuegbaren Tools eigenstaendig, wenn sie zur Loesung der Aufgabe "
    "beitragen."
)


class Agent:
    def __init__(
        self,
        client: AsyncAnthropic,
        model: str,
        tools: ToolRegistry,
        ui_hub: UIHub | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._tools = tools
        self._history: list[MessageParam] = []
        self._ui_hub = ui_hub

    async def _emit(self, event_type: str, **payload: object) -> None:
        if self._ui_hub is not None:
            await self._ui_hub.emit(event_type, **payload)

    async def handle_turn(self, user_text: str) -> str:
        await self._emit("user_message", text=user_text)
        await self._emit("status", state="thinking")
        self._history.append({"role": "user", "content": user_text})

        while True:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=self._tools.to_anthropic_tools(),
                messages=self._history,
            )
            self._history.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                reply = "".join(
                    block.text for block in response.content if block.type == "text"
                )
                await self._emit("assistant_message", text=reply)
                await self._emit("status", state="idle")
                return reply

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            for block in tool_use_blocks:
                logger.info("Tool-Aufruf: %s(%s)", block.name, block.input)
                await self._emit("tool_call", name=block.name, input=block.input)

            results = await asyncio.gather(
                *(self._tools.dispatch(b.name, b.input) for b in tool_use_blocks)
            )
            self._history.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": b.id, "content": r}
                        for b, r in zip(tool_use_blocks, results)
                    ],
                }
            )
