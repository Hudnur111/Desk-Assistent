import asyncio
import wave
from pathlib import Path
from typing import Protocol

import numpy as np


class AudioSink(Protocol):
    async def play(self, pcm: np.ndarray, sample_rate: int) -> None: ...


class SpeakerSink:
    async def play(self, pcm: np.ndarray, sample_rate: int) -> None:
        import sounddevice as sd

        await asyncio.to_thread(sd.play, pcm, sample_rate, blocking=True)


class WavFileSink:
    """Schreibt Audio in eine WAV-Datei statt auf einen Lautsprecher.

    Dient als Ersatz fuer echte Audio-Hardware bei Tests und in
    Umgebungen ohne Audio-Devices.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    async def play(self, pcm: np.ndarray, sample_rate: int) -> None:
        def _write() -> None:
            with wave.open(str(self._path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm.astype(np.int16).tobytes())

        await asyncio.to_thread(_write)
