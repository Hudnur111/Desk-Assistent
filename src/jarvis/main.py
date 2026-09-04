import asyncio
import datetime as dt
import logging
from pathlib import Path

from anthropic import AsyncAnthropic

from jarvis.agent.core import Agent
from jarvis.audio.sinks import SpeakerSink
from jarvis.audio.sources import MicrophoneSource
from jarvis.audio.stt import SpeechToText
from jarvis.audio.tts import TextToSpeech
from jarvis.audio.vad import EnergyVAD
from jarvis.audio.wakeword import WakeWordDetector
from jarvis.brain import BrainStore
from jarvis.config import Settings
from jarvis.logging_setup import configure_logging
from jarvis.memory import MemoryStore
from jarvis.pipeline import VoicePipeline
from jarvis.resource_monitor import log_resource_usage_periodically
from jarvis.scheduler import DailyBriefingTrigger
from jarvis.tools.brain import brain_tools
from jarvis.tools.builtin import builtin_tools
from jarvis.tools.documents import document_tools
from jarvis.tools.email import ImapEmailBackend, build_email_draft_tool
from jarvis.tools.registry import ToolRegistry
from jarvis.ui.hub import UIHub
from jarvis.ui.server import create_app
from jarvis.watchdog import notify_ready, run_watchdog_heartbeat

logger = logging.getLogger(__name__)

EXIT_WORDS = {"exit", "quit"}


async def _read_console_input(queue: "asyncio.Queue[str]") -> None:
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
    for tool in document_tools():
        registry.register(tool)
    brain = BrainStore(Path(settings.brain_path)) if settings.brain_enabled else None
    if brain is not None:
        for tool in brain_tools(brain):
            registry.register(tool)
    if settings.imap_host and settings.email_address and settings.email_password:
        backend = ImapEmailBackend(
            host=settings.imap_host,
            username=settings.email_address,
            password=settings.email_password,
            drafts_folder=settings.email_drafts_folder,
        )
        registry.register(build_email_draft_tool(backend))
    else:
        logger.info(
            "E-Mail-Tool deaktiviert: JARVIS_IMAP_HOST/JARVIS_EMAIL_ADDRESS/"
            "JARVIS_EMAIL_PASSWORD nicht vollstaendig gesetzt"
        )

    ui_hub = UIHub() if settings.ui_enabled else None

    memory = MemoryStore(Path(settings.memory_path)) if settings.memory_enabled else None
    initial_history = await memory.load() if memory is not None else None

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    agent = Agent(
        client=client,
        model=settings.model,
        tools=registry,
        ui_hub=ui_hub,
        memory=memory,
        brain=brain,
        initial_history=initial_history,
        max_context_messages=settings.memory_max_messages,
    )

    queue: "asyncio.Queue[str]" = asyncio.Queue()
    tasks = [
        asyncio.create_task(_read_console_input(queue)),
        asyncio.create_task(log_resource_usage_periodically(ui_hub=ui_hub)),
        asyncio.create_task(run_watchdog_heartbeat()),
    ]
    await notify_ready()

    if settings.daily_briefing_time:
        hour, _, minute = settings.daily_briefing_time.partition(":")
        briefing = DailyBriefingTrigger(
            output_queue=queue, at=dt.time(int(hour), int(minute))
        )
        tasks.append(asyncio.create_task(briefing.run()))

    if settings.ui_enabled:
        import uvicorn

        assert ui_hub is not None
        config = uvicorn.Config(
            create_app(ui_hub),
            host=settings.ui_host,
            port=settings.ui_port,
            log_level="warning",
        )
        tasks.append(asyncio.create_task(uvicorn.Server(config).serve()))
        logger.info("Display-UI unter http://%s:%d", settings.ui_host, settings.ui_port)

    tts: TextToSpeech | None = None
    sink: SpeakerSink | None = None
    if settings.voice_enabled:
        if not settings.piper_model_path:
            raise RuntimeError(
                "JARVIS_VOICE_ENABLED=true erfordert JARVIS_PIPER_MODEL_PATH"
            )
        pipeline = VoicePipeline(
            source=MicrophoneSource(),
            wakeword=WakeWordDetector(model_names=list(settings.wakeword_models)),
            stt=SpeechToText(model_size=settings.whisper_model_size),
            vad=EnergyVAD(),
            output_queue=queue,
            ui_hub=ui_hub,
        )
        tasks.append(asyncio.create_task(pipeline.run()))
        tts = TextToSpeech(
            model_path=Path(settings.piper_model_path),
            config_path=Path(settings.piper_config_path)
            if settings.piper_config_path
            else None,
        )
        sink = SpeakerSink()

    mode = "Text + Sprache" if settings.voice_enabled else "Text"
    print(f"Jarvis bereit ({mode}). 'exit' zum Beenden.\n")
    try:
        while True:
            user_text = await queue.get()
            if not user_text or user_text.lower() in EXIT_WORDS:
                break
            reply = await agent.handle_turn(user_text)
            print(f"Jarvis: {reply}\n")
            if tts is not None and sink is not None:
                if ui_hub is not None:
                    await ui_hub.emit("status", state="speaking")
                pcm, sample_rate = await tts.synthesize(reply)
                await sink.play(pcm, sample_rate)
                if ui_hub is not None:
                    await ui_hub.emit("status", state="idle")
    finally:
        for task in tasks:
            task.cancel()
        await client.close()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
