# Desk Assistant 🤖

**AI Desktop Client** für Raspberry Pi 4B — kombiniert [Ollama](https://ollama.com) (lokal) und [Claude](https://anthropic.com) (Cloud) in einer professionellen VS Code-style Oberfläche.

## Features

- **Dual AI** — Ollama (lokal, kostenlos) + Claude API (Cloud)
- **VS Code Design** — Dark theme, professionelles Layout
- **MCP Foundation** — Model Context Protocol Tool-Registrierung
- **Skills System** — Vordefinierte Prompts für beide AIs
- **GitHub Sync** — Automatische Synchronisation
- **Streaming** — Echtzeit-Antworten mit Stopp-Funktion
- **Markdown Rendering** — Code-Highlighting, GFM-Support

## Schnellstart

### Windows (Entwicklung)
```bat
scripts\start.bat
```

### Raspberry Pi
```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

### Manuell
```bash
npm install
npm run build
npm start
# → http://localhost:3000
```

## Erster Start

Beim ersten Öffnen erscheint der Setup-Wizard:
1. **Ollama** — URL konfigurieren (Standard: `http://localhost:11434`)
2. **Claude** — Optional: API Key von [console.anthropic.com](https://console.anthropic.com)

## Ollama installieren (Raspberry Pi)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2        # ~2GB
ollama pull mistral         # ~4GB (optional)
```

## Struktur

```
├── src/
│   ├── app/               # Next.js App Router
│   │   ├── api/chat/      # Unified AI Streaming Endpoint
│   │   ├── api/ollama/    # Ollama Proxy
│   │   ├── api/mcp/       # MCP Tool Executor
│   │   ├── api/sync/      # GitHub Sync API
│   │   └── setup/         # First-run Setup
│   ├── components/        # React UI Komponenten
│   ├── stores/            # Zustand State Management
│   └── lib/
│       ├── mcp/           # MCP Registry
│       └── skills/        # Skills Loader
├── skills/
│   ├── ollama/index.json  # Ollama Skills
│   └── claude/index.json  # Claude Skills
└── scripts/
    ├── start.bat          # Windows Launcher
    ├── start.sh           # Linux/Pi Launcher
    └── sync.sh            # GitHub Sync
```

## MCP Tools

| Tool | Beschreibung | Status |
|------|-------------|--------|
| `get_time` | Datum & Uhrzeit | ✅ Aktiv |
| `github_sync` | GitHub Synchronisation | ✅ Aktiv |
| `file_read` | Lokale Dateien lesen | ⬜ Optional |
| `web_search` | Web-Suche | ⬜ Optional |
| `run_code` | Code ausführen | ⬜ Optional |

## GitHub Sync

```bash
./scripts/sync.sh
# oder im Chat: Sidebar → GitHub Sync Button
```

---
*Läuft auf Raspberry Pi 4B · Next.js · Ollama · Claude API*
