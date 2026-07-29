import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    model: str = "claude-sonnet-5"
    log_level: str = "INFO"

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
        )
