import asyncio
import wave
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

import numpy as np

from . import FRAME_SAMPLES, SAMPLE_RATE


class AudioSource(Protocol):
    def frames(self) -> AsyncIterator[np.ndarray]: ...


class MicrophoneSource:
    """Streamt Mono-int16-Audio vom Standard-Eingabegeraet in feste Frames."""

    def __init__(
        self, sample_rate: int = SAMPLE_RATE, frame_samples: int = FRAME_SAMPLES
    ) -> None:
        self._sample_rate = sample_rate
        self._frame_samples = frame_samples

    async def frames(self) -> AsyncIterator[np.ndarray]:
        import sounddevice as sd

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[np.ndarray] = asyncio.Queue()

        def _callback(indata, frame_count, time_info, status) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, indata.copy().reshape(-1))

        with sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self._frame_samples,
            callback=_callback,
        ):
            while True:
                yield await queue.get()


class WavFileSource:
    """Liest eine 16kHz/mono/16-bit-WAV-Datei framehweise ein.

    Dient als Ersatz fuer echtes Mikrofon-Hardware bei Tests und in
    Umgebungen ohne Audio-Devices.
    """

    def __init__(self, path: Path, frame_samples: int = FRAME_SAMPLES) -> None:
        self._path = path
        self._frame_samples = frame_samples

    async def frames(self) -> AsyncIterator[np.ndarray]:
        with wave.open(str(self._path), "rb") as wav_file:
            if (
                wav_file.getframerate() != SAMPLE_RATE
                or wav_file.getsampwidth() != 2
                or wav_file.getnchannels() != 1
            ):
                raise ValueError(
                    f"Erwarte {SAMPLE_RATE}Hz/mono/16-bit WAV, bekam "
                    f"{wav_file.getframerate()}Hz/{wav_file.getnchannels()}ch/"
                    f"{wav_file.getsampwidth() * 8}bit"
                )
            while True:
                raw = wav_file.readframes(self._frame_samples)
                if not raw:
                    return
                yield np.frombuffer(raw, dtype=np.int16)
                await asyncio.sleep(0)
