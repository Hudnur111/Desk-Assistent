import asyncio
from collections.abc import AsyncIterator

import numpy as np
import pytest

from jarvis.audio.vad import EnergyVAD
from jarvis.pipeline import VoicePipeline

SILENCE = np.zeros(1280, dtype=np.int16)
LOUD = np.full(1280, 8000, dtype=np.int16)


class FakeAudioSource:
    def __init__(self, frames: list[np.ndarray]) -> None:
        self._frames = frames

    async def frames(self) -> AsyncIterator[np.ndarray]:
        for frame in self._frames:
            yield frame


class FakeWakeWordDetector:
    """Loest bei den angegebenen Aufruf-Indizes aus (Zaehlung nur, waehrend
    die Pipeline auf ein Wake-Word wartet)."""

    def __init__(self, trigger_indices: set[int] | None = None, name: str = "hey_jarvis") -> None:
        self._trigger_indices = trigger_indices
        self._name = name
        self._seen = 0

    async def detect(self, frame: np.ndarray) -> str | None:
        index = self._seen
        self._seen += 1
        if self._trigger_indices is None or index in self._trigger_indices:
            return self._name
        return None


class FakeSTT:
    def __init__(self, transcript: str) -> None:
        self._transcript = transcript
        self.calls = 0

    async def transcribe(self, audio: np.ndarray, language: str | None = "de") -> str:
        self.calls += 1
        return self._transcript


@pytest.mark.asyncio
async def test_pipeline_ignores_frames_before_wakeword() -> None:
    # Die ersten beiden (stillen) Frames werden nur zur Wake-Word-Erkennung
    # genutzt und duerfen nicht in die Aufnahme einfliessen. Das dritte
    # (laute) Frame loest das Wake-Word aus; die eigentliche Aeusserung
    # (zwei laute Frames) folgt danach.
    frames = [SILENCE, SILENCE, LOUD, LOUD, LOUD, SILENCE, SILENCE]
    stt = FakeSTT("hallo jarvis")
    queue: asyncio.Queue[str] = asyncio.Queue()

    pipeline = VoicePipeline(
        source=FakeAudioSource(frames),
        wakeword=FakeWakeWordDetector(trigger_indices={2}),
        stt=stt,
        vad=EnergyVAD(threshold=500.0, silence_frames_to_stop=2),
        output_queue=queue,
    )
    await pipeline.run()

    assert stt.calls == 1
    assert queue.qsize() == 1
    assert queue.get_nowait() == "hallo jarvis"


@pytest.mark.asyncio
async def test_pipeline_aborts_if_no_speech_after_wakeword() -> None:
    frames = [LOUD] + [SILENCE] * 30
    stt = FakeSTT("sollte nicht aufgerufen werden")
    queue: asyncio.Queue[str] = asyncio.Queue()

    pipeline = VoicePipeline(
        source=FakeAudioSource(frames),
        wakeword=FakeWakeWordDetector(trigger_indices={0}),
        stt=stt,
        vad=EnergyVAD(threshold=500.0, silence_frames_to_stop=3),
        output_queue=queue,
        max_silence_before_speech=5,
    )
    await pipeline.run()

    assert stt.calls == 0
    assert queue.qsize() == 0


@pytest.mark.asyncio
async def test_pipeline_handles_multiple_utterances_sequentially() -> None:
    utterance = [LOUD, LOUD, SILENCE, SILENCE, SILENCE]
    frames = [SILENCE] + utterance + [SILENCE] + utterance
    stt = FakeSTT("hallo")
    queue: asyncio.Queue[str] = asyncio.Queue()

    pipeline = VoicePipeline(
        source=FakeAudioSource(frames),
        wakeword=FakeWakeWordDetector(trigger_indices={0, 1}),
        stt=stt,
        vad=EnergyVAD(threshold=500.0, silence_frames_to_stop=3),
        output_queue=queue,
    )
    await pipeline.run()

    assert stt.calls == 2
    assert queue.qsize() == 2
