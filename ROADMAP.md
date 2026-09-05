# Jarvis-Desk-Assistant — Entwicklungs-Roadmap

Aufbauend auf [ARCHITECTURE.md](./ARCHITECTURE.md). Jede Phase liefert ein lauffähiges Zwischenergebnis.

## Phase 0 — Fundament
- Raspberry Pi OS Lite (64-bit), Python 3.11 venv (oder Docker-Basis)
- Projektskelett: Config-Management (`.env`), Logging, Tool-Registry-Pattern
- Entscheidung: Docker Compose vs. venv+systemd

## Phase 1 — Konsolen-MVP (Text-Agent) ✅
- Async Kern-Loop: stdin → Claude API (Tool-Use) → stdout
- 2–3 einfache Tools (z. B. Notiz speichern, Datei lesen/schreiben)
- Etabliert das Async-Architekturmuster für alle weiteren Phasen

## Phase 2 — Sprach-I/O ✅ (Code fertig, Hardware-Test steht aus)
- `faster-whisper` (STT) mit VAD + Wake-Word (`openWakeWord`)
- `Piper` (TTS)
- Vollständig non-blocking Pipeline: Mikro-Stream → VAD → Whisper → Agent → Piper → Lautsprecher
- Umgesetzt als zusätzlicher Producer in dieselbe Agent-Queue wie die Konsole
  (`src/jarvis/pipeline.py`), Audio-I/O hinter `AudioSource`/`AudioSink`-
  Schnittstellen abstrahiert, mit Unit-Tests gegen Fakes abgesichert
  (`tests/test_pipeline.py`, `tests/test_vad.py`, `tests/test_audio_io.py`).
  **Offen:** Verifikation mit echter Mikrofon-/Lautsprecher-Hardware und
  echten Modell-Downloads auf dem Ziel-Pi (in der Entwicklungs-Sandbox nicht
  möglich, da kein Audio-Device und `huggingface.co` per Netzwerk-Policy
  blockiert sind).

## Phase 3 — Büro-Automatisierung ✅ (Code fertig, Live-Versand ungetestet)
- Tool: E-Mail-Entwürfe per IMAP APPEND (App-Passwort statt vollem OAuth-Flow,
  spart eine schwere Google-API-Abhängigkeit auf dem Pi) — `tools/email.py`
- Tool: Dokument-Erstellung/-Bearbeitung/-Lesen (`.docx` via `python-docx`) —
  `tools/documents.py`, vollständig offline getestet
- Sicherheits-Bestätigungsschritt vor sendenden Aktionen: das Tool legt nur
  einen Entwurf ab, Versenden bleibt bewusst ein manueller Schritt im
  E-Mail-Client
- **Offen:** Live-Verifikation des IMAP-Entwurfs gegen ein echtes Postfach
  (in der Sandbox nicht möglich)

## Phase 4 — Display-UI ✅ (visuell verifiziert, Kiosk-Autostart auf dem Pi offen)
- FastAPI + WebSocket-Server (`ui/server.py`) mit `UIHub` (`ui/hub.py`) als
  Pub/Sub-Fanout: State-Broadcast (hört zu/denkt nach/spricht/bereit),
  Nachrichtenverlauf, Tool-Aufrufe
- HTML/CSS/JS-Frontend (`ui/static/`) im Avengers-/Cyberpunk-HUD-Stil:
  animierter Ring (Puls/Rotation je Zustand), Wellenform-Balken beim Sprechen,
  farbcodiertes Terminal-Log. Bewusst ohne Tailwind-Build-Schritt umgesetzt
  (handgeschriebenes CSS) - kein Node.js auf dem Pi nötig, einfacher als in
  ARCHITECTURE.md skizziert
- `Agent` und `VoicePipeline` senden optional (`ui_hub`-Parameter) Events;
  ohne aktivierte UI bleibt das Verhalten unveraendert (No-Op)
- Getestet: `UIHub`-Fanout, WebSocket-Endpunkt (FastAPI TestClient), Agent-
  Event-Sequenz mit Fake-Client (`tests/test_ui_hub.py`,
  `tests/test_ui_server.py`, `tests/test_agent_ui_events.py`) sowie visuell
  mit echtem headless Chromium via Playwright (alle vier Zustände + Log
  gerendert und geprüft)
- Kiosk-Autostart-Artefakt bereits erstellt (`deploy/autostart/jarvis-kiosk.desktop`,
  Phase 6) - **Offen:** Lasttest der GPU-Beschleunigung unter echtem Raspberry Pi OS

## Phase 5 — Autonomie & Feinschliff ✅
- Persistenter Memory-Layer über Sessions hinweg — `src/jarvis/memory.py`
  (`MemoryStore`, JSON-Datei), in `Agent` eingebunden (`initial_history` beim
  Start laden, nach jedem Turn speichern); per Round-Trip-Tests abgesichert
- Proaktive Aktionen — `src/jarvis/scheduler.py` (`DailyBriefingTrigger`):
  legt zu fester Uhrzeit selbststaendig einen Briefing-Prompt in dieselbe
  Queue wie Konsole/Sprache; Zeitlogik mit injizierbarer Uhr/Sleep-Funktion
  getestet (kein echtes Warten in Tests noetig)
- systemd-Watchdog — `src/jarvis/watchdog.py`: sd_notify-Protokoll direkt per
  Unix-Datagram-Socket (keine libsystemd-Abhaengigkeit), `notify_ready()` +
  periodischer Heartbeat; end-to-end mit echtem gebundenem Socket getestet
- Ressourcen-Profiling — `src/jarvis/resource_monitor.py`: periodisches
  RSS/CPU-Logging ueber die stdlib (`resource`-Modul, kein `psutil`);
  Whisper-Modellgroesse bleibt ueber `JARVIS_WHISPER_MODEL` konfigurierbar
  (Default `tiny`, passend fuer den Pi 4)
- Robuste Fehlerbehandlung als Teil dieser Phase vorgezogen: `Agent` faengt
  `anthropic.APIError` ab, rollt den Verlauf sauber zurueck, liefert eine
  deutsche Fallback-Antwort — verifiziert gegen die echte API mit
  ungueltigem Key (401 korrekt abgefangen, kein Absturz)
- In `main.py` verdrahtet: Memory-Load beim Start, Resource-Monitor- und
  Watchdog-Heartbeat-Tasks laufen immer, Briefing-Task nur wenn
  `JARVIS_DAILY_BRIEFING_TIME` gesetzt ist

## Phase 6 — Härtung ✅ (Docker-Build in der Sandbox nicht testbar)
- `Dockerfile` + `docker-compose.yml` + `.dockerignore` fuer Container-Betrieb
  als Alternative zu systemd+venv
- `deploy/systemd/jarvis.service` (Type=notify, WatchdogSec=30,
  Restart=always) und `deploy/autostart/jarvis-kiosk.desktop` fuer
  Chromium-Kiosk-Autostart, dokumentiert in `deploy/README.md`
- Secrets-Management: bewusst `.env` (gitignored) statt Vault/Secret-Manager —
  angemessen fuer ein Einzelnutzer-Pi-Projekt, keine zusaetzliche Infrastruktur
- Offline-Fallback bei Netzwerkausfall / robuste Fehlerbehandlung: siehe
  Phase 5 (API-Fehlerpfad des Agenten)
- Tests fuer Agent-Loop und Tool-Dispatch: durchgehend vorhanden
  (`test_agent_ui_events.py`, `test_agent_error_handling.py`,
  `test_tool_registry.py`), 42 Tests insgesamt, alle gruen
- **Offen:** Docker-Build wurde in dieser Sandbox aktiv versucht (Docker-Daemon
  laief, `docker build` ausgefuehrt) — schlaegt beim Pull von `python:3.11-slim`
  fehl, weil `production.cloudfront.docker.com` (Docker Hub Blob-Storage) per
  Netzwerk-Policy nicht erreichbar ist (per direktem Curl-Test verifiziert,
  nicht nur vermutet). Muss auf einer Maschine mit Docker-Hub-Zugriff
  (z. B. dem Pi) gebaut/verifiziert werden.

## Phase 7 — Das Gehirn ✅
- Langzeitgedaechtnis als PARA-strukturierter, Obsidian-kompatibler
  Markdown-Vault (`src/jarvis/brain.py`, `BrainStore`) — getrennt vom
  Kurzzeitverlauf (`memory.py`)
- `capture()` legt Notizen nach exaktem Titel upsertend an; ein Titel-Slug-
  Kollisionsfall (zwei verschiedene Titel ergeben denselben Dateinamen) wird
  per Zeitstempel-Suffix aufgeloest statt still zu ueberschreiben
- `log_turn()` protokolliert jeden Dialog kompakt in der Daily-Note der Inbox
  (reines Datei-I/O, kein zusaetzlicher API-Tokenverbrauch)
- Suche (`search()`/`context_block()`) laeuft ueber Keyword-Matching (stdlib,
  kein Embedding-Modell/keine neue Abhaengigkeit); Snippets werden aus dem
  Frontmatter-bereinigten Notiztext gezogen; der Kontext-Block fuer den
  System-Prompt ist per `max_chars` gedeckelt
- Tools `save_to_brain`/`search_brain` (`tools/brain.py`) geben dem Agenten
  eigenstaendigen Zugriff aufs Gehirn
- `Agent._windowed_history()` begrenzt den an die API gesendeten Verlauf auf
  `JARVIS_MEMORY_MAX_MESSAGES` Nachrichten, immer an vollstaendigen
  Turn-Grenzen geschnitten (nie mitten in einem Tool-Use/Tool-Result-Paar) —
  das volle Gedaechtnis bleibt ueber `MemoryStore`/`BrainStore` erhalten
- 19 Tests (`test_brain.py`, `test_tool_brain.py`, `test_agent_brain.py`),
  62 Tests insgesamt, alle gruen
- Optional per `JARVIS_BRAIN_ENABLED` (Standard `true`), Pfad ueber
  `JARVIS_BRAIN_PATH` (Standard `data/brain`) — 1:1 als Obsidian-Vault
  oeffenbar; ein befuelltes Referenz-Vault mit derselben PARA-Struktur liegt
  als Vorlage im Branch `feature/obsidian-brain-system`
