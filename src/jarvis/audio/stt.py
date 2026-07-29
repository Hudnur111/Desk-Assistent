import asyncio
from pathlib import Path

import numpy as np


class SpeechToText:
    def __init__(
        self, model_size: str = "tiny", device: str = "cpu", compute_type: str = "int8"
    ) -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)

    async def transcribe(self, audio: np.ndarray | Path, language: str | None = "de") -> str:
        def _run() -> str:
            source = str(audio) if isinstance(audio, Path) else audio.astype(np.float32) / 32768.0
            segments, _ = self._model.transcribe(source, language=language)
            return " ".join(segment.text.strip() for segment in segments).strip()

        return await asyncio.to_thread(_run)
