import asyncio
import json
from pathlib import Path


class MemoryStore:
    """Persistiert den Gespraechsverlauf als JSON-Datei ueber Neustarts hinweg."""

    def __init__(self, path: Path) -> None:
        self._path = path

    async def load(self) -> list[dict]:
        def _read() -> list[dict]:
            if not self._path.is_file():
                return []
            return json.loads(self._path.read_text(encoding="utf-8"))

        return await asyncio.to_thread(_read)

    async def save(self, history: list[dict]) -> None:
        def _write() -> None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        await asyncio.to_thread(_write)
