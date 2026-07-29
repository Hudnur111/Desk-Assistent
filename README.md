# Jarvis-Desk-Assistant

Autonomer, sprach- und UI-gesteuerter Assistent für Raspberry Pi 4B — IT-Consulting, Büro-Automatisierung und agentisches Tool-Handling im Avengers-/Cyberpunk-Stil.

- Architektur & Technologie-Entscheidungen: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Entwicklungs-Roadmap: [ROADMAP.md](./ROADMAP.md)

## Status

Phase 1 (Konsolen-MVP) ist umgesetzt: ein asynchroner Agent-Loop mit Tool-Registry
und drei Beispiel-Tools (`get_current_time`, `save_note`, `read_file`).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env   # ANTHROPIC_API_KEY eintragen
```

## Starten

```bash
set -a && source .env && set +a
.venv/bin/jarvis
```