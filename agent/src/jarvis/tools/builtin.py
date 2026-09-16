import asyncio
import datetime
from pathlib import Path

from .base import Tool

NOTES_DIR = Path("data/notes")


async def _get_current_time() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


async def _save_note(title: str, content: str) -> str:
    def _write() -> Path:
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        path = NOTES_DIR / f"{title}.md"
        path.write_text(content, encoding="utf-8")
        return path

    path = await asyncio.to_thread(_write)
    return f"Notiz gespeichert unter {path}"


async def _read_file(path: str) -> str:
    file_path = Path(path)

    def _read() -> str | None:
        if not file_path.is_file():
            return None
        return file_path.read_text(encoding="utf-8")

    content = await asyncio.to_thread(_read)
    if content is None:
        return f"Datei nicht gefunden: {path}"
    return content


def builtin_tools() -> list[Tool]:
    return [
        Tool(
            name="get_current_time",
            description="Gibt die aktuelle lokale Uhrzeit zurueck.",
            input_schema={"type": "object", "properties": {}},
            handler=_get_current_time,
        ),
        Tool(
            name="save_note",
            description="Speichert eine Notiz als Markdown-Datei unter data/notes/.",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Dateiname ohne Endung",
                    },
                    "content": {
                        "type": "string",
                        "description": "Inhalt der Notiz",
                    },
                },
                "required": ["title", "content"],
            },
            handler=_save_note,
        ),
        Tool(
            name="read_file",
            description="Liest den Inhalt einer Textdatei.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Pfad zur Datei"}
                },
                "required": ["path"],
            },
            handler=_read_file,
        ),
    ]
