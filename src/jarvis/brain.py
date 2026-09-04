"""Das Gehirn: persistentes Langzeitgedaechtnis als PARA-strukturierter Markdown-Vault.

Kompatibel mit Obsidian (YAML-Frontmatter, `[[Wiki-Links]]`-faehige Notizen).
Suche laeuft rein ueber Keyword-Matching (stdlib, kein Embedding-Modell) -
das haelt Prompt-Kontext klein und kostet keine zusaetzlichen API-Tokens.
"""
import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_CATEGORY_DIRS = {
    "inbox": "00-Inbox",
    "projects": "10-Projects",
    "areas": "20-Areas",
    "resources": "30-Resources",
}

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_SLUG_RE = re.compile(r"[^\w\- ]+", re.UNICODE)


@dataclass(frozen=True)
class BrainMatch:
    title: str
    path: Path
    snippet: str
    score: int


def _slugify(title: str) -> str:
    return _SLUG_RE.sub("", title).strip().replace(" ", "-") or "note"


def _best_snippet(text: str, keywords: set[str], width: int = 160) -> str:
    lower = text.lower()
    for keyword in keywords:
        idx = lower.find(keyword)
        if idx != -1:
            start = max(0, idx - width // 2)
            end = min(len(text), idx + width // 2)
            return text[start:end].replace("\n", " ").strip()
    return text[:width].replace("\n", " ").strip()


class BrainStore:
    """Schreibt und durchsucht das Gehirn (Obsidian-kompatibler PARA-Vault)."""

    def __init__(self, vault_path: Path) -> None:
        self._vault = vault_path

    def category_dir(self, category: str) -> Path:
        return self._vault / _CATEGORY_DIRS.get(category, _CATEGORY_DIRS["inbox"])

    async def capture(
        self,
        title: str,
        content: str,
        category: str = "inbox",
        tags: list[str] | None = None,
    ) -> Path:
        def _write() -> Path:
            directory = self.category_dir(category)
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"{_slugify(title)}.md"
            frontmatter = (
                "---\n"
                f"title: {title}\n"
                f"created: {datetime.now().isoformat(timespec='seconds')}\n"
                f"tags: [{', '.join(tags or [])}]\n"
                "---\n\n"
            )
            path.write_text(f"{frontmatter}# {title}\n\n{content}\n", encoding="utf-8")
            return path

        return await asyncio.to_thread(_write)

    async def log_turn(self, user_text: str, assistant_text: str) -> Path:
        """Haengt einen Gespraechseintrag an die heutige Daily-Note an.

        Reines Datei-I/O - kein zusaetzlicher API-Tokenverbrauch.
        """

        def _write() -> Path:
            directory = self.category_dir("inbox")
            directory.mkdir(parents=True, exist_ok=True)
            today = datetime.now()
            path = directory / f"Daily-{today.strftime('%Y-%m-%d')}.md"
            entry = f"## {today.strftime('%H:%M')}\n**Du:** {user_text}\n\n**Jarvis:** {assistant_text}\n\n"
            if not path.is_file():
                header = (
                    "---\n"
                    f"title: Daily {today.strftime('%Y-%m-%d')}\n"
                    f"created: {today.isoformat(timespec='seconds')}\n"
                    "tags: [daily-log]\n"
                    "---\n\n"
                    f"# {today.strftime('%Y-%m-%d')}\n\n"
                )
                path.write_text(header + entry, encoding="utf-8")
            else:
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(entry)
            return path

        return await asyncio.to_thread(_write)

    async def search(self, query: str, limit: int = 5) -> list[BrainMatch]:
        def _search() -> list[BrainMatch]:
            keywords = {w.lower() for w in _WORD_RE.findall(query) if len(w) > 2}
            if not keywords or not self._vault.is_dir():
                return []
            matches: list[BrainMatch] = []
            for md_path in self._vault.rglob("*.md"):
                text = md_path.read_text(encoding="utf-8", errors="ignore")
                lower = text.lower()
                score = sum(lower.count(kw) for kw in keywords)
                if score == 0:
                    continue
                title_line = next(
                    (line for line in text.splitlines() if line.startswith("# ")),
                    md_path.stem,
                )
                matches.append(
                    BrainMatch(
                        title=title_line.lstrip("# ").strip(),
                        path=md_path,
                        snippet=_best_snippet(text, keywords),
                        score=score,
                    )
                )
            matches.sort(key=lambda m: m.score, reverse=True)
            return matches[:limit]

        return await asyncio.to_thread(_search)

    async def context_block(self, query: str, max_chars: int = 1200) -> str:
        """Kompakter, token-sparsamer Kontext-Block fuer den System-Prompt."""
        matches = await self.search(query, limit=5)
        if not matches:
            return ""
        lines = ["## Relevanter Kontext aus dem Gehirn"]
        used = len(lines[0])
        for match in matches:
            line = f"- **{match.title}**: {match.snippet}"
            if used + len(line) > max_chars:
                break
            lines.append(line)
            used += len(line)
        return "\n".join(lines) if len(lines) > 1 else ""
