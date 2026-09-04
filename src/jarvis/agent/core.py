import asyncio
import logging

import anthropic
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from ..brain import BrainStore
from ..memory import MemoryStore
from ..tools.registry import ToolRegistry
from ..ui.hub import UIHub

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Du bist Jarvis, ein autonomer Assistent fuer IT-Consulting und "
    "Buero-Automatisierung. Antworte praezise auf Deutsch. Nutze die "
    "verfuegbaren Tools eigenstaendig, wenn sie zur Loesung der Aufgabe "
    "beitragen."
)

API_ERROR_REPLY = (
    "Entschuldigung, ich kann gerade keine Verbindung zur KI-API herstellen. "
    "Bitte versuche es in Kuerze erneut."
)


def _serialize_content(content: object) -> object:
    if isinstance(content, str):
        return content
    return [
        block if isinstance(block, dict) else block.model_dump() for block in content
    ]


class Agent:
    def __init__(
        self,
        client: AsyncAnthropic,
        model: str,
        tools: ToolRegistry,
        ui_hub: UIHub | None = None,
        memory: MemoryStore | None = None,
        brain: BrainStore | None = None,
        initial_history: list[MessageParam] | None = None,
        max_context_messages: int = 20,
    ) -> None:
        self._client = client
        self._model = model
        self._tools = tools
        self._history: list[MessageParam] = (
            list(initial_history) if initial_history else []
        )
        self._ui_hub = ui_hub
        self._memory = memory
        self._brain = brain
        self._max_context_messages = max_context_messages

    async def _emit(self, event_type: str, **payload: object) -> None:
        if self._ui_hub is not None:
            await self._ui_hub.emit(event_type, **payload)

    async def handle_turn(self, user_text: str) -> str:
        await self._emit("user_message", text=user_text)
        await self._emit("status", state="thinking")

        history_len_before = len(self._history)
        self._history.append({"role": "user", "content": user_text})

        system_prompt = SYSTEM_PROMPT
        if self._brain is not None:
            context = await self._brain.context_block(user_text)
            if context:
                system_prompt = f"{SYSTEM_PROMPT}\n\n{context}"

        api_error = False
        try:
            reply = await self._run_loop(system_prompt)
        except anthropic.APIError as exc:
            logger.error("Claude-API nicht erreichbar: %s", exc)
            del self._history[history_len_before:]
            reply = API_ERROR_REPLY
            api_error = True

        await self._emit("assistant_message", text=reply)
        await self._emit("status", state="idle")

        if self._memory is not None:
            await self._memory.save(self._history)
        if self._brain is not None and not api_error:
            await self._brain.log_turn(user_text, reply)

        return reply

    def _windowed_history(self) -> list[MessageParam]:
        """Begrenzt den an die API gesendeten Verlauf auf vollstaendige Turns.

        Spart Input-Tokens bei langen Sitzungen; das vollstaendige Gedaechtnis
        bleibt ueber `MemoryStore`/`BrainStore` erhalten.
        """
        if len(self._history) <= self._max_context_messages:
            return self._history
        turn_starts = [
            i
            for i, m in enumerate(self._history)
            if m["role"] == "user" and isinstance(m["content"], str)
        ]
        if not turn_starts:
            return self._history
        cutoff = next(
            (s for s in turn_starts if len(self._history) - s <= self._max_context_messages),
            turn_starts[-1],
        )
        return self._history[cutoff:]

    async def _run_loop(self, system_prompt: str) -> str:
        while True:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=system_prompt,
                tools=self._tools.to_anthropic_tools(),
                messages=self._windowed_history(),
            )
            self._history.append(
                {"role": "assistant", "content": _serialize_content(response.content)}
            )

            if response.stop_reason != "tool_use":
                return "".join(
                    block.text for block in response.content if block.type == "text"
                )

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
