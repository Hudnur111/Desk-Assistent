import asyncio
from pathlib import Path

import numpy as np


class TextToSpeech:
    def __init__(self, model_path: Path, config_path: Path | None = None) -> None:
        from piper.voice import PiperVoice

        self._voice = PiperVoice.load(
            str(model_path), config_path=str(config_path) if config_path else None
        )

    async def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        def _run() -> tuple[np.ndarray, int]:
            chunks = list(self._voice.synthesize(text))
            pcm_bytes = b"".join(chunk.audio_int16_bytes for chunk in chunks)
            return np.frombuffer(pcm_bytes, dtype=np.int16), self._voice.config.sample_rate

        return await asyncio.to_thread(_run)
