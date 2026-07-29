import asyncio
import logging

import numpy as np

from .audio.sources import AudioSource
from .audio.stt import SpeechToText
from .audio.vad import EnergyVAD
from .audio.wakeword import WakeWordDetector
from .ui.hub import UIHub

logger = logging.getLogger(__name__)


class VoicePipeline:
    """Wake-Word -> VAD-gesteuerte Aufnahme -> STT.

    Erkannte Aeusserungen landen als Text in derselben Queue, aus der auch
    die Konsolen-Eingabe gespeist wird - Text- und Spracheingabe bedienen so
    parallel denselben Agenten.
    """

    def __init__(
        self,
        source: AudioSource,
        wakeword: WakeWordDetector,
        stt: SpeechToText,
        vad: EnergyVAD,
        output_queue: "asyncio.Queue[str]",
        max_utterance_frames: int = 250,
        max_silence_before_speech: int = 25,
        ui_hub: UIHub | None = None,
    ) -> None:
        self._source = source
        self._wakeword = wakeword
        self._stt = stt
        self._vad = vad
        self._output_queue = output_queue
        self._max_utterance_frames = max_utterance_frames
        self._max_silence_before_speech = max_silence_before_speech
        self._ui_hub = ui_hub

    async def _emit(self, event_type: str, **payload: object) -> None:
        if self._ui_hub is not None:
            await self._ui_hub.emit(event_type, **payload)

    async def run(self) -> None:
        listening_buffer: list[np.ndarray] | None = None
        heard_speech = False
        silence_before_speech = 0

        async for frame in self._source.frames():
            if listening_buffer is None:
                wake = await self._wakeword.detect(frame)
                if wake is not None:
                    logger.info("Wake-Word erkannt: %s", wake)
                    listening_buffer = []
                    heard_speech = False
                    silence_before_speech = 0
                    self._vad.reset()
                    await self._emit("status", state="listening")
                continue

            listening_buffer.append(frame)
            if self._vad.is_speech(frame):
                heard_speech = True

            if not heard_speech:
                silence_before_speech += 1
                if silence_before_speech >= self._max_silence_before_speech:
                    logger.info("Keine Sprache nach Wake-Word, breche Aufnahme ab")
                    listening_buffer = None
                    await self._emit("status", state="idle")
                continue

            stop = (
                self._vad.should_stop(frame)
                or len(listening_buffer) >= self._max_utterance_frames
            )
            if not stop:
                continue

            audio = np.concatenate(listening_buffer)
            listening_buffer = None
            text = await self._stt.transcribe(audio)
            if text:
                await self._output_queue.put(text)
            else:
                logger.info("Keine Sprache erkannt, verwerfe Aufnahme")
                await self._emit("status", state="idle")
