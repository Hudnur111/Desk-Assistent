import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    model: str = "claude-sonnet-5"
    log_level: str = "INFO"
    voice_enabled: bool = False
    whisper_model_size: str = "tiny"
    wakeword_models: tuple[str, ...] = field(default_factory=lambda: ("hey_jarvis",))
    piper_model_path: str | None = None
    piper_config_path: str | None = None
    imap_host: str | None = None
    email_address: str | None = None
    email_password: str | None = None
    email_drafts_folder: str = "[Gmail]/Drafts"
    ui_enabled: bool = False
    ui_host: str = "127.0.0.1"
    ui_port: int = 8000
    memory_enabled: bool = True
    memory_path: str = "data/history.json"
    daily_briefing_time: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY ist nicht gesetzt. Siehe .env.example."
            )
        return cls(
            anthropic_api_key=api_key,
            model=os.environ.get("JARVIS_MODEL", cls.model),
            log_level=os.environ.get("JARVIS_LOG_LEVEL", cls.log_level),
            voice_enabled=os.environ.get("JARVIS_VOICE_ENABLED", "false").lower() == "true",
            whisper_model_size=os.environ.get("JARVIS_WHISPER_MODEL", cls.whisper_model_size),
            wakeword_models=tuple(
                os.environ.get("JARVIS_WAKEWORD_MODELS", "hey_jarvis").split(",")
            ),
            piper_model_path=os.environ.get("JARVIS_PIPER_MODEL_PATH") or None,
            piper_config_path=os.environ.get("JARVIS_PIPER_CONFIG_PATH") or None,
            imap_host=os.environ.get("JARVIS_IMAP_HOST") or None,
            email_address=os.environ.get("JARVIS_EMAIL_ADDRESS") or None,
            email_password=os.environ.get("JARVIS_EMAIL_PASSWORD") or None,
            email_drafts_folder=os.environ.get(
                "JARVIS_EMAIL_DRAFTS_FOLDER", cls.email_drafts_folder
            ),
            ui_enabled=os.environ.get("JARVIS_UI_ENABLED", "false").lower() == "true",
            ui_host=os.environ.get("JARVIS_UI_HOST", cls.ui_host),
            ui_port=int(os.environ.get("JARVIS_UI_PORT", cls.ui_port)),
            memory_enabled=os.environ.get("JARVIS_MEMORY_ENABLED", "true").lower()
            == "true",
            memory_path=os.environ.get("JARVIS_MEMORY_PATH", cls.memory_path),
            daily_briefing_time=os.environ.get("JARVIS_DAILY_BRIEFING_TIME") or None,
        )
