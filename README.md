# Jarvis

Persönlicher KI-Desk-Assistent mit Chat, Sprache, Langzeitgedächtnis und
Office-Automatisierung. Zwei Komponenten, eine Identität:

- **`/web`** – Next.js Chat-/Sprach-Oberfläche, gehostet auf Vercel. Von
  überall erreichbar (Handy, Laptop, Browser).
- **`/agent`** – Python-Agent, der lokal auf deinem PC (oder Raspberry Pi)
  läuft. Er hat Zugriff auf dein Dateisystem, steuert Word/Excel/PowerPoint/
  Outlook via COM, führt Konsole/Sprach-I/O aus und schreibt jeden
  Gesprächsverlauf in ein Obsidian-kompatibles Gehirn (`/agent/data/brain`).

## Warum zwei Teile?

Vercel ist eine Cloud-/Serverless-Plattform – sie hat keinen Zugriff auf
Dateien, Mikrofon oder installierte Programme auf deinem PC. Alles, was
"wie ein Kollege am Schreibtisch" arbeiten soll (Word/Excel/Outlook
automatisieren, Dateien lesen/schreiben, ein persistentes Gedächtnis
führen), muss lokal laufen. Die Web-App ist die Oberfläche, die von
überall erreichbar ist; der lokale Agent ist die Arbeitskraft mit echtem
System-Zugriff. Beide teilen sich dieselbe Persönlichkeit (System-Prompt),
laufen aber unabhängig – es gibt aktuell keine automatische Fernsteuerung
des lokalen Agenten über die Cloud-UI hinweg (siehe "Grenzen" unten).

## `/web` – Cloud-Chat (Vercel)

```bash
cd web
npm install
cp .env.example .env.local   # ANTHROPIC_API_KEY eintragen
npm run dev
```

Öffne `http://localhost:3000`. Chat mit Streaming-Antworten, Mikrofon-Input
(Web Speech API) und Sprachausgabe (SpeechSynthesis).

**Deploy auf Vercel:**

```bash
npm i -g vercel
cd web
vercel
```

Environment Variable `ANTHROPIC_API_KEY` im Vercel-Projekt-Dashboard setzen.

## `/agent` – Lokaler Coworker (PC / Raspberry Pi)

```bash
cd agent
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
# Nur auf Windows für Office-Automatisierung zusätzlich:
.venv/bin/pip install -e ".[windows]"
cp .env.example .env   # ANTHROPIC_API_KEY eintragen
set -a && source .env && set +a
.venv/bin/jarvis
```

**Features:**

- **Chat/Konsole** – Text-Ein-/Ausgabe direkt im Terminal
- **Sprache** – Wake-Word → VAD → STT (Whisper) → TTS (Piper),
  `JARVIS_VOICE_ENABLED=true`
- **Display-UI** – Cyberpunk-HUD im Browser, `JARVIS_UI_ENABLED=true` →
  `http://127.0.0.1:8000`
- **Dateiformate** (plattformunabhängig) – Word/Excel/PowerPoint-Dateien
  erstellen/lesen (`python-docx`, `openpyxl`, `python-pptx`)
- **Office-Live-Steuerung** (nur Windows, `pywin32`) – direkte
  COM-Automatisierung installierter Word/Excel/PowerPoint/Outlook-Apps,
  inkl. Words nativer Rechtschreib-/Grammatikprüfung und automatischer
  Korrektur
- **E-Mail-Entwürfe** – IMAP-Draft (plattformunabhängig) oder
  Outlook-COM-Draft (Windows) – wird nie automatisch versendet
- **Gehirn** (`BrainStore`, Obsidian-kompatibel) – jeder Gesprächsturn wird
  automatisch als Daily-Log gespeichert; PARA-Struktur
  (Projects/Areas/Resources/Inbox) für kuratierte Notizen;
  Keyword-Suche liefert token-sparsamen Kontext an jeden neuen Turn –
  **alles bleibt dauerhaft gespeichert**, über Neustarts hinweg
- **Kurzzeitgedächtnis** (`MemoryStore`) – kompletter Gesprächsverlauf als
  JSON, wird bei jedem Start geladen

Details zu Autostart/systemd/Kiosk-Modus auf dem Pi: [`agent/deploy/README.md`](./agent/deploy/README.md).

## Grenzen (ehrlich gesagt)

- Die Vercel-Web-App kann **nicht** den lokalen Agenten fernsteuern oder
  auf deine lokalen Office-Dateien zugreifen – das wäre ein Sicherheitsloch
  (fremde Server mit Zugriff auf deinen PC). Für "von überall auf meinen
  PC zugreifen" nutze stattdessen einen Tunnel (ngrok/SSH) auf die
  Display-UI des lokalen Agenten, oder Remote-Desktop.
- COM-Automatisierung funktioniert nur unter Windows mit installiertem
  Microsoft Office.
- Sprach-Feature (Wake-Word/STT/TTS) braucht Mikrofon/Lautsprecher-Hardware
  und wurde in der Entwicklungs-Sandbox nur mit Fake-Audio-Quellen
  getestet.

## Tests

```bash
cd agent
.venv/bin/pytest tests/ -v
```
