import wave
from pathlib import Path

import numpy as np
import pytest

from jarvis.audio import SAMPLE_RATE
from jarvis.audio.sinks import WavFileSink
from jarvis.audio.sources import WavFileSource


def _write_wav(path: Path, samples: np.ndarray) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(samples.tobytes())


@pytest.mark.asyncio
async def test_wav_file_source_yields_all_samples_in_order(tmp_path: Path) -> None:
    samples = np.arange(0, 4000, dtype=np.int16)
    wav_path = tmp_path / "in.wav"
    _write_wav(wav_path, samples)

    source = WavFileSource(wav_path, frame_samples=1280)
    collected: list[np.ndarray] = []
    async for frame in source.frames():
        collected.append(frame)

    reconstructed = np.concatenate(collected)
    np.testing.assert_array_equal(reconstructed, samples)


@pytest.mark.asyncio
async def test_wav_file_source_rejects_wrong_sample_rate(tmp_path: Path) -> None:
    wav_path = tmp_path / "wrong_rate.wav"
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8000)
        wav_file.writeframes(np.zeros(100, dtype=np.int16).tobytes())

    source = WavFileSource(wav_path)
    with pytest.raises(ValueError):
        async for _ in source.frames():
            pass


@pytest.mark.asyncio
async def test_wav_file_sink_writes_readable_pcm(tmp_path: Path) -> None:
    pcm = np.array([0, 100, -100, 32000, -32000], dtype=np.int16)
    out_path = tmp_path / "out.wav"

    sink = WavFileSink(out_path)
    await sink.play(pcm, SAMPLE_RATE)

    with wave.open(str(out_path), "rb") as wav_file:
        assert wav_file.getframerate() == SAMPLE_RATE
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        written = np.frombuffer(wav_file.readframes(wav_file.getnframes()), dtype=np.int16)

    np.testing.assert_array_equal(written, pcm)
