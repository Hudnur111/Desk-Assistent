# Jarvis-Desk-Assistant

Autonomer, sprach- und UI-gesteuerter Assistent für Raspberry Pi 4B — IT-Consulting, Büro-Automatisierung und agentisches Tool-Handling im Avengers-/Cyberpunk-Stil.

- Architektur & Technologie-Entscheidungen: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Entwicklungs-Roadmap: [ROADMAP.md](./ROADMAP.md)

## Status

- **Phase 1 (Konsolen-MVP):** asynchroner Agent-Loop mit Tool-Registry und drei
  Beispiel-Tools (`get_current_time`, `save_note`, `read_file`).
- **Phase 2 (Sprach-I/O):** Wake-Word (`openWakeWord`) → VAD-gesteuerte Aufnahme →
  STT (`faster-whisper`) → Agent → TTS (`Piper`), als zusätzlicher Producer/Consumer
  parallel zur Konsoleneingabe (`src/jarvis/pipeline.py`, `src/jarvis/audio/`).
  Optional per `JARVIS_VOICE_ENABLED=true` aktivierbar; Text- und Sprachmodus
  laufen gleichzeitig über dieselbe Agent-Queue.

  Hinweis: Modell-Downloads (Whisper-Gewichte, Piper-Stimmen) sowie Mikrofon-/
  Lautsprecher-Hardware sind in der Entwicklungs-Sandbox nicht verfügbar. Die
  Audio-Module sind daher gegen `AudioSource`/`AudioSink`-Schnittstellen gebaut
  (`WavFileSource`/`WavFileSink` als Hardware-Ersatz) und per Unit-Tests mit
  Fakes abgedeckt (`tests/`); der volle Hardware-Pfad muss auf dem Pi verifiziert
  werden.
- **Phase 3 (Büro-Automatisierung):** Tools `create_document`/`append_to_document`/
  `read_document` (`python-docx`, voll offline getestet) sowie `create_email_draft`
  (IMAP-APPEND in den Drafts-Ordner, App-Passwort statt OAuth). Die E-Mail sendet
  nie automatisch - Versenden bleibt bewusst ein manueller Schritt im E-Mail-Client.
  Das E-Mail-Tool wird nur registriert, wenn `JARVIS_IMAP_HOST`,
  `JARVIS_EMAIL_ADDRESS` und `JARVIS_EMAIL_PASSWORD` gesetzt sind.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env   # ANTHROPIC_API_KEY eintragen
```

## Starten

```bash
set -a && source .env && set +a
.venv/bin/jarvis
```

Für Sprachmodus zusätzlich in `.env` setzen: `JARVIS_VOICE_ENABLED=true`,
`JARVIS_PIPER_MODEL_PATH=/pfad/zu/stimme.onnx` (siehe `.env.example`).

Für E-Mail-Entwürfe zusätzlich `JARVIS_IMAP_HOST`, `JARVIS_EMAIL_ADDRESS` und
`JARVIS_EMAIL_PASSWORD` (App-Passwort) setzen.

## Tests

```bash
.venv/bin/pytest tests/ -v
```