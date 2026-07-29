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
        )
