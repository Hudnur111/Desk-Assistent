import logging
from typing import Any

from .base import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' ist bereits registriert")
        self._tools[tool.name] = tool

    def to_anthropic_tools(self) -> list[dict[str, Any]]:
        return [tool.to_anthropic_schema() for tool in self._tools.values()]

    async def dispatch(self, name: str, tool_input: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Fehler: unbekanntes Tool '{name}'"
        try:
            return await tool.handler(**tool_input)
        except Exception as exc:
            logger.exception("Tool '%s' ist fehlgeschlagen", name)
            return f"Fehler bei Tool '{name}': {exc}"
