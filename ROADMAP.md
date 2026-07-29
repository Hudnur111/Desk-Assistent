# Jarvis-Desk-Assistant — Entwicklungs-Roadmap

Aufbauend auf [ARCHITECTURE.md](./ARCHITECTURE.md). Jede Phase liefert ein lauffähiges Zwischenergebnis.

## Phase 0 — Fundament
- Raspberry Pi OS Lite (64-bit), Python 3.11 venv (oder Docker-Basis)
- Projektskelett: Config-Management (`.env`), Logging, Tool-Registry-Pattern
- Entscheidung: Docker Compose vs. venv+systemd

## Phase 1 — Konsolen-MVP (Text-Agent)
- Async Kern-Loop: stdin → Claude API (Tool-Use) → stdout
- 2–3 einfache Tools (z. B. Notiz speichern, Datei lesen/schreiben)
- Etabliert das Async-Architekturmuster für alle weiteren Phasen

## Phase 2 — Sprach-I/O
- `faster-whisper` (STT) mit VAD + Wake-Word (`openWakeWord`)
- `Piper` (TTS)
- Vollständig non-blocking Pipeline: Mikro-Stream → VAD → Whisper → Agent → Piper → Lautsprecher

## Phase 3 — Büro-Automatisierung
- Tool: E-Mail-Entwürfe (Gmail API / IMAP)
- Tool: Dokument-Erstellung/-Bearbeitung (docx/pdf)
- Sicherheits-Bestätigungsschritt vor sendenden/verändernden Aktionen

## Phase 4 — Display-UI
- FastAPI + WebSocket-Server (State-Broadcast: hört zu/denkt/spricht, Verlauf, Tool-Aufrufe)
- HTML/CSS/JS-Frontend im Avengers-/Cyberpunk-HUD-Stil (Wellenform-/Arc-Reactor-Visualizer)
- Chromium-Kiosk-Autostart; Lasttest → ggf. Wechsel auf CustomTkinter

## Phase 5 — Autonomie & Feinschliff
- Persistenter Memory-Layer über Sessions hinweg
- Proaktive Aktionen (z. B. Kalender-Check, Briefings)
- `systemd`-Services für alle Komponenten inkl. Watchdog/Auto-Restart
- Ressourcen-Profiling (CPU/RAM), Whisper-Modellgröße feinjustieren

## Phase 6 — Härtung
- Docker-Compose-Packaging, Secrets-Management
- Offline-Fallback bei Netzwerkausfall, robuste Fehlerbehandlung
- Tests für Agent-Loop und Tool-Dispatch
