# Desk Assistant 🤖

**AI Desktop Client** für Raspberry Pi 4B — kombiniert [Ollama](https://ollama.com) (lokal) und [Claude](https://anthropic.com) (Cloud) in einer professionellen VS Code-style Oberfläche, mit automatischem GitHub-Deployment.

---

## Auto-Deploy: GitHub → Raspberry Pi

Bei jedem `git push` auf `main` deployed GitHub Actions **automatisch** auf deinen Pi.

```
git push → GitHub Actions → Runner auf Pi → git pull + npm build + systemctl restart
```

Kein Port-Forwarding nötig — der Pi verbindet sich selbst zu GitHub.

### Einmaliges Setup (auf dem Pi ausführen)

**Schritt 1 — Vollinstallation:**
```bash
curl -fsSL https://raw.githubusercontent.com/Hudnur111/Desk-Assistent/main/scripts/setup-pi.sh | bash
```

Installiert: Node.js, Ollama, App, systemd Service, Chromium-Autostart.

**Schritt 2 — GitHub Actions Runner:**
```bash
# Token von: https://github.com/Hudnur111/Desk-Assistent/settings/actions/runners/new
RUNNER_TOKEN=<token> bash scripts/setup-runner.sh
```

Runner registriert sich als `pi-<hostname>` und startet als systemd Service.

**Schritt 3 — Sudo-Berechtigung (für Restart ohne Passwort):**
```bash
sudo cp deploy/desk-assistant-sudoers /etc/sudoers.d/desk-assistant
```

**Fertig!** Ab jetzt → `git push` → Pi updated sich automatisch.

---

## Features

| Feature | Beschreibung |
|---------|-------------|
| **Dual-AI** | Ollama (lokal) + Claude API |
| **VS Code Design** | Dark theme, professionelles Layout |
| **Streaming** | Echtzeit-Antworten |
| **MCP Foundation** | Tool-Registry erweiterbar |
| **Skills** | Vordefinierte Prompts für beide AIs |
| **Auto-Deploy** | GitHub → Pi via Actions Runner |
| **Chromium Kiosk** | Öffnet sich beim Pi-Start automatisch |

---

## Manueller Start

```bash
# Windows (Dev)
scripts\start.bat

# Raspberry Pi
./scripts/start.sh

# Manuell
npm install && npm run build && npm start
```

---

## Deployment-Übersicht

```
.github/workflows/deploy-pi.yml   → GitHub Actions Workflow
scripts/setup-pi.sh               → Vollinstallation (einmalig)
scripts/setup-runner.sh           → Runner-Setup (einmalig)
deploy/desk-assistant.service     → systemd Unit
deploy/desk-assistant-kiosk.desktop → Chromium Autostart
deploy/desk-assistant-sudoers     → Sudo-Berechtigung
```

---

## Befehle auf dem Pi

```bash
# Service Status
systemctl status desk-assistant

# Live Logs
journalctl -u desk-assistant -f

# Manuell updaten
cd ~/Desk-Assistent && git pull && npm run build && sudo systemctl restart desk-assistant

# Runner Status
journalctl -u actions.runner.* -f
```

---

## Ollama Modelle

```bash
ollama pull llama3.2      # 2GB — empfohlen für Pi 4B (4GB RAM)
ollama pull mistral       # 4GB — für 8GB RAM
ollama list               # installierte Modelle
```

---

## Struktur

```
src/
├── app/
│   ├── api/chat/         → Streaming: Ollama + Claude
│   ├── api/mcp/          → MCP Tool Executor
│   ├── api/sync/         → GitHub Sync
│   └── setup/            → First-run Wizard
├── components/           → TitleBar, Sidebar, ChatPanel, StatusBar
├── stores/               → Zustand State
└── lib/
    ├── mcp/              → MCP Registry
    └── skills/           → Skills Loader
skills/
├── ollama/index.json     → 6 Ollama Skills
└── claude/index.json     → 6 Claude Skills
scripts/
├── start.bat             → Windows Launcher
├── start.sh              → Pi Launcher
├── setup-pi.sh           → Vollinstallation
├── setup-runner.sh       → Runner Setup
└── sync.sh               → Manueller Sync
deploy/
├── desk-assistant.service
├── desk-assistant-kiosk.desktop
└── desk-assistant-sudoers
.github/workflows/
└── deploy-pi.yml         → Auto-Deploy Pipeline
```
