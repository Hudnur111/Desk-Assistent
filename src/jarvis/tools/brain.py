from ..brain import BrainStore
from .base import Tool


def brain_tools(brain: BrainStore) -> list[Tool]:
    async def _save(title: str, content: str, category: str = "inbox") -> str:
        path = await brain.capture(title=title, content=content, category=category)
        return f"Im Gehirn gespeichert: {path}"

    async def _search(query: str) -> str:
        matches = await brain.search(query)
        if not matches:
            return "Keine Treffer im Gehirn."
        return "\n".join(f"- {m.title}: {m.snippet}" for m in matches)

    return [
        Tool(
            name="save_to_brain",
            description=(
                "Speichert eine Notiz dauerhaft im Gehirn (PARA-strukturierter "
                "Obsidian-Vault). category: inbox|projects|areas|resources."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Titel der Notiz"},
                    "content": {"type": "string", "description": "Inhalt der Notiz"},
                    "category": {
                        "type": "string",
                        "enum": ["inbox", "projects", "areas", "resources"],
                        "description": "PARA-Kategorie, Standard: inbox",
                    },
                },
                "required": ["title", "content"],
            },
            handler=_save,
        ),
        Tool(
            name="search_brain",
            description=(
                "Durchsucht das Gehirn nach frueheren Notizen und Gespraechen "
                "zu einem Thema."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Suchbegriff"}
                },
                "required": ["query"],
            },
            handler=_search,
        ),
    ]
