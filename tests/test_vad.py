import numpy as np

from jarvis.audio.vad import EnergyVAD

SILENCE = np.zeros(1280, dtype=np.int16)
LOUD = np.full(1280, 8000, dtype=np.int16)


def test_is_speech_detects_loud_frame_and_ignores_silence() -> None:
    vad = EnergyVAD(threshold=500.0)
    assert vad.is_speech(LOUD) is True
    assert vad.is_speech(SILENCE) is False


def test_should_stop_after_enough_consecutive_silence_frames() -> None:
    vad = EnergyVAD(threshold=500.0, silence_frames_to_stop=3)

    assert vad.should_stop(LOUD) is False
    assert vad.should_stop(SILENCE) is False
    assert vad.should_stop(SILENCE) is False
    assert vad.should_stop(SILENCE) is True


def test_speech_frame_resets_silence_run() -> None:
    vad = EnergyVAD(threshold=500.0, silence_frames_to_stop=2)

    assert vad.should_stop(SILENCE) is False
    assert vad.should_stop(LOUD) is False
    assert vad.should_stop(SILENCE) is False
    assert vad.should_stop(SILENCE) is True


def test_reset_clears_silence_run() -> None:
    vad = EnergyVAD(threshold=500.0, silence_frames_to_stop=2)

    vad.should_stop(SILENCE)
    vad.reset()
    assert vad.should_stop(SILENCE) is False
