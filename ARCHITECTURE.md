# Jarvis-Desk-Assistant — Architektur-Entscheidung (ADR-001)

Status: Vorschlag / Basis für Entwicklung
Ziel-Hardware: Raspberry Pi 4B (4–8 GB RAM), HDMI-Display angeschlossen

## 1. Hardware-Empfehlung

| Komponente | Empfehlung | Begründung |
|---|---|---|
| Mikrofon | **ReSpeaker Mic Array v2.0 (USB, 4-Kanal)** | XMOS-Chip macht Beamforming + Rauschunterdrückung + AEC in Hardware, entlastet den Pi. Alternative für Minimal-Setup: USB-Konferenzmikro mit Hardware-AEC (z. B. Anker PowerConf S3) — plug & play, kein Treiber-Ärger. |
| Lautsprecher | Kompakter **USB-Lautsprecher** (kein I2S-DAC) | Vermeidet zusätzliche Codec-/ALSA-Konfiguration; funktioniert zusammen mit AEC-Mikro ohne Echo-Probleme. |
| Display | Vorhandenes HDMI-Display, idealerweise mit **Touch** (z. B. offizielles 7"/10.1" Touchdisplay) | Touch als Fallback-Interaktion neben Sprache, passt zum "HUD"-Look. |
| Gehäuse/Kühlung | **Aktiv gekühltes Gehäuse** (z. B. Argon ONE) | Whisper-Inferenz + Dauerbetrieb erzeugen Last; Throttling verhindern. |
| Netzteil | Offizielles Pi4-USB-C-Netzteil (5V/3A) | Mikro + Lautsprecher + Display ziehen zusätzlichen Strom. |

## 2. Technologie-Stack

**Sprache: Python 3.11+ mit `asyncio`** (nicht Go/Rust)

Begründung:
- Die rechenintensiven Teile laufen bereits in kompilierten C++-Backends: `faster-whisper` nutzt CTranslate2, `Piper` ist ein kompiliertes Binary. Die Orchestrierungs-Schicht ist I/O-bound (Warten auf Audio, API-Antworten, WebSocket-Events) — genau das Einsatzgebiet von `asyncio`.
- Go/Rust würden Rohleistung bringen, aber der Flaschenhals liegt nicht im Orchestrierungscode, sondern in ML-Inferenz (ausgelagert) und Netzwerklatenz zur Claude-API. Der Umstieg würde Komplexität erhöhen ohne spürbaren Pi-Entlastungseffekt.
- Python hat das reifste Ökosystem für alle benötigten Bausteine: Anthropic SDK, FastAPI, httpx (async), Audio-Bindings.
- Ausweichoption offen halten: Sollte ein einzelner Hot-Path (z. B. Audio-Preprocessing) sich später als CPU-Engpass erweisen, per PyO3 gezielt nach Rust auslagern — keine Vorab-Entscheidung nötig.

**UI: FastAPI + WebSockets (Backend) + HTML5/Tailwind (vorkompiliert) + Chromium Kiosk-Mode (Frontend)**

Begründung:
- Kein Electron/Node.js — stattdessen nativer Chromium-Browser im Kiosk-Modus, den der Pi 4 GPU-beschleunigt rendern kann (VideoCore VI), solange die UI auf CSS-Animationen/SVG statt schweren JS-Frameworks (React/Vue) setzt.
- WebSockets erlauben Echtzeit-Updates (Status "hört zu" / "denkt" / "spricht", Tool-Aufrufe, Chat-Verlauf) ohne Polling.
- Alternative/Fallback bei zu hoher Chromium-Last: **CustomTkinter** — natives, leichteres UI ohne Browser-Engine, weniger Animationsfreiheit, aber geringerer Ressourcenverbrauch. Entscheidung nach erstem Belastungstest auf echter Hardware (Phase 4).

**Audio:**
- STT: `faster-whisper`, Modell `tiny` oder `base`, mit Voice-Activity-Detection (VAD) davor, um Dauer-Transkription zu vermeiden.
- Wake-Word: `openWakeWord` (offline, leichtgewichtig) — verhindert, dass STT permanent läuft und CPU frisst.
- TTS: `Piper`, deutsches oder englisches Voice-Modell je nach gewünschter Sprache.

**KI/Agent:**
- Anthropic Claude API via natives Tool-Use (Function Calling) — kein LangChain o. ä., da zu schwergewichtig für den Zweck. Ein schlanker eigener Async-Tool-Dispatch-Loop reicht.

**Isolation:** Docker Compose (ein Service je Komponente: `agent-core`, `stt-tts-worker`, `ui-server`) oder einheitliches `venv` mit `systemd`-Services — Entscheidung in Phase 0.

## 3. Offene Entscheidungspunkte für spätere Phasen
- Chromium-Kiosk vs. CustomTkinter: nach Lasttest auf realer Hardware entscheiden.
- Persistenter Speicher/Memory-Layer (Vector-Store vs. strukturierte Datei) — Phase 5.
- Docker vs. reines venv+systemd — Phase 0, je nach gewünschtem Isolationsgrad vs. Overhead.
