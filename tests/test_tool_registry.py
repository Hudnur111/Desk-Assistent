import pytest

from jarvis.tools.base import Tool
from jarvis.tools.registry import ToolRegistry


async def _echo(value: str) -> str:
    return f"echo:{value}"


async def _boom() -> str:
    raise ValueError("kaputt")


def _make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="echo",
            description="Gibt den Wert zurueck",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            handler=_echo,
        )
    )
    registry.register(
        Tool(
            name="boom",
            description="Wirft immer einen Fehler",
            input_schema={"type": "object", "properties": {}},
            handler=_boom,
        )
    )
    return registry


@pytest.mark.asyncio
async def test_dispatch_runs_registered_tool() -> None:
    registry = _make_registry()
    result = await registry.dispatch("echo", {"value": "hallo"})
    assert result == "echo:hallo"


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_returns_error_text() -> None:
    registry = _make_registry()
    result = await registry.dispatch("does_not_exist", {})
    assert "unbekanntes Tool" in result


@pytest.mark.asyncio
async def test_dispatch_catches_handler_exceptions() -> None:
    registry = _make_registry()
    result = await registry.dispatch("boom", {})
    assert "Fehler bei Tool 'boom'" in result


def test_register_duplicate_name_raises() -> None:
    registry = _make_registry()
    with pytest.raises(ValueError):
        registry.register(
            Tool(
                name="echo",
                description="doppelt",
                input_schema={"type": "object", "properties": {}},
                handler=_echo,
            )
        )


def test_to_anthropic_tools_matches_schema_shape() -> None:
    registry = _make_registry()
    schemas = registry.to_anthropic_tools()
    names = {schema["name"] for schema in schemas}
    assert names == {"echo", "boom"}
    for schema in schemas:
        assert set(schema.keys()) == {"name", "description", "input_schema"}
