import asyncio
import logging

from anthropic import AsyncAnthropic

from jarvis.agent.core import Agent
from jarvis.config import Settings
from jarvis.logging_setup import configure_logging
from jarvis.tools.builtin import builtin_tools
from jarvis.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

EXIT_WORDS = {"exit", "quit"}


async def _read_console_input(queue: asyncio.Queue[str]) -> None:
    loop = asyncio.get_running_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, input, "Du: ")
        except EOFError:
            await queue.put("exit")
            return
        text = line.strip()
        if text:
            await queue.put(text)
        if text.lower() in EXIT_WORDS:
            return


async def run() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)

    registry = ToolRegistry()
    for tool in builtin_tools():
        registry.register(tool)

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    agent = Agent(client=client, model=settings.model, tools=registry)

    queue: asyncio.Queue[str] = asyncio.Queue()
    reader_task = asyncio.create_task(_read_console_input(queue))

    print("Jarvis-Konsole bereit. 'exit' zum Beenden.\n")
    try:
        while True:
            user_text = await queue.get()
            if not user_text or user_text.lower() in EXIT_WORDS:
                break
            reply = await agent.handle_turn(user_text)
            print(f"Jarvis: {reply}\n")
    finally:
        reader_task.cancel()
        await client.close()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
