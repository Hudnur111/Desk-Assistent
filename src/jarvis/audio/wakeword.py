import asyncio

import numpy as np


class WakeWordDetector:
    def __init__(self, model_names: list[str], threshold: float = 0.5) -> None:
        from openwakeword.model import Model

        self._model = Model(wakeword_models=model_names, inference_framework="onnx")
        self._threshold = threshold

    async def detect(self, frame: np.ndarray) -> str | None:
        def _predict() -> str | None:
            scores = self._model.predict(frame)
            for name, score in scores.items():
                if score > self._threshold:
                    return name
            return None

        return await asyncio.to_thread(_predict)
