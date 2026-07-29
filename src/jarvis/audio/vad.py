import numpy as np


class EnergyVAD:
    """RMS-Energie-VAD: erkennt Sprechpausen anhand der Lautstaerke.

    Bewusst ohne zusaetzliche native Abhaengigkeit (z. B. webrtcvad)
    gehalten, um den Pi 4 nicht unnoetig zu belasten.
    """

    def __init__(self, threshold: float = 500.0, silence_frames_to_stop: int = 12) -> None:
        self._threshold = threshold
        self._silence_frames_to_stop = silence_frames_to_stop
        self._silence_run = 0

    def is_speech(self, frame: np.ndarray) -> bool:
        rms = float(np.sqrt(np.mean(frame.astype(np.float64) ** 2)))
        return rms > self._threshold

    def reset(self) -> None:
        self._silence_run = 0

    def should_stop(self, frame: np.ndarray) -> bool:
        if self.is_speech(frame):
            self._silence_run = 0
        else:
            self._silence_run += 1
        return self._silence_run >= self._silence_frames_to_stop
