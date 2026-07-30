# Deployment auf dem Raspberry Pi 4

## Erstinstallation

```bash
git clone https://github.com/Hudnur111/Desk-Assistent.git ~/jarvis
sudo bash ~/jarvis/deploy/bootstrap-pi.sh
```

Installiert System-Pakete, venv, `.env` (aus `.env.example`), die systemd-Unit
und die sudo-Regel fuer den Auto-Deploy. Ist idempotent und laesst eine
bestehende `.env`, `data/` und `.venv/` unangetastet. Pfad und Benutzer werden
aus dem sudo-Aufrufer abgeleitet und in die Unit eingesetzt - `JARVIS_APP_DIR`
und `JARVIS_USER` ueberschreiben das.

Danach `ANTHROPIC_API_KEY` in `~/jarvis/.env` eintragen und
`sudo systemctl start jarvis.service`.

Zusaetzlich installiert `bootstrap-pi.sh`:

* **Python 3.11 per `uv`** fuer das venv, unabhaengig vom System-Python.
  Debian trixie liefert nur Python 3.13 aus, dafuer gibt es aber kein
  `tflite-runtime`-Wheel (Hard-Dependency von `openwakeword`, von Google nur
  bis 3.11 gebaut). `uv python install 3.11` laedt einen fertigen Build in
  Sekunden statt stundenlang aus Quellcode zu kompilieren.
* **Gehaeuse-Luefter dauerhaft an** ueber `gpio=<pin>=op,dh` in
  `/boot/firmware/config.txt` (Default-Pin: `JARVIS_FAN_GPIO=10`, leer setzen
  zum Deaktivieren). Das ist eine reine Firmware-Direktive - der Pin wird
  schon vor dem Kernel als Ausgang auf HIGH gesetzt, kein Kernel-Overlay,
  kein eigener Dienst, keine Temperatursteuerung. Greift erst nach einem
  Neustart (`sudo reboot`).

## Automatischer Deploy bei jedem Push

Zwei Wege stehen zur Wahl, beide fuehren `deploy/update.sh` aus (siehe unten).
`bootstrap-pi.sh` richtet standardmaessig Variante A ein.

### A) Polling-Timer (Default, braucht keinen Token)

`jarvis-update.timer` pollt alle 90s per `git fetch`, ob `origin/main` weiter
ist als der lokale Stand, und deployt dann automatisch. Da das Repo oeffentlich
ist, braucht das keine Anmeldung bei GitHub - kein Token, kein Runner, keine
Portfreigabe. Nachteil: bis zu ~90s Verzoegerung statt Sekunden.

Laeuft nach `bootstrap-pi.sh` bereits automatisch. Manuell pruefen:

```bash
systemctl status jarvis-update.timer
journalctl -u jarvis-update.service -n 50
```

### B) GitHub-Actions-Self-Hosted-Runner (optional, schneller)

Braucht einen Registrierungs-Token von GitHub (`Settings -> Actions ->
Runners -> New self-hosted runner`) - bewusst ein manueller Schritt, der nicht
automatisiert wird. Dafuer deployt jeder Push innerhalb von Sekunden statt
bis zu 90s.

```bash
bash ~/jarvis/deploy/install-runner.sh
```

Gibt danach die drei Befehle aus, die den Token brauchen (`config.sh`,
`svc.sh install`, `svc.sh start`). Sobald der Runner laeuft, sollte der
Polling-Timer gestoppt werden, um doppelte/ueberlappende Deploys zu vermeiden:

```bash
sudo systemctl disable --now jarvis-update.timer
```

### Ablauf eines Deploys (beide Varianten)

1. Ausloeser: Timer-Tick (Variante A) oder `.github/workflows/deploy-pi.yml`
   auf dem Runner mit Label `jarvis-pi` (Variante B).
2. `deploy/update.sh` macht `git fetch` + `reset --hard origin/main` in
   `/home/pi/jarvis` - ist der lokale Stand schon aktuell, passiert nichts.
3. Hat sich `pyproject.toml` geaendert, laeuft `pip install -e .` nach.
4. `sudo systemctl restart jarvis.service`. Wegen `Type=notify` kehrt der
   Befehl erst zurueck, wenn sich der Dienst als bereit gemeldet hat.
5. Schlaegt der Start fehl, rollt `update.sh` automatisch auf den vorherigen
   Commit zurueck und startet den alten Stand wieder - der Assistent bleibt
   also auch nach einem kaputten Commit lauffaehig.

`.env`, `.venv/` und `data/` stehen in `.gitignore` und werden vom Deploy nie
angefasst. Es laeuft kein `git clean`.

Manuell nachziehen geht in beiden Varianten jederzeit:

```bash
bash ~/jarvis/deploy/update.sh
```

Die sudo-Regel in `/etc/sudoers.d/jarvis-deploy` erlaubt genau zwei Befehle
ohne Passwort - Neustart von `jarvis.service` und `jarvis-status.service`.
Kein allgemeines NOPASSWD.

## Status-Endpunkt fuer das Dashboard

`jarvis-status.service` liefert unter `http://<pi>:8090/` ein komplettes
Live-Dashboard (`deploy/dashboard/index.html`) - von jedem Geraet im selben
Netz per Browser aufrufbar (Handy, Laptop, ...), ohne dass ein anderer Rechner
laufen muss. `/status` liefert dieselben Daten als JSON, `/health` antwortet
nur `ok` fuer externe Uptime-Checks.

Das Dashboard fragt standardmaessig relativ zur eigenen Origin ab (`fetch("status")`)
- da es vom Pi selbst ausgeliefert wird, ist "die eigene Origin" automatisch
der richtige Pi. Ueber das Einstellungs-Icon lassen sich Host/Port manuell
setzen, falls die Seite stattdessen einen *anderen* Pi im Netz abfragen soll.

Drei Entscheidungen dahinter:

* **Eigener Dienst, nicht Teil von `jarvis.service`.** Ein Monitor, der mit dem
  ueberwachten Prozess zusammen stirbt, kann nicht melden, dass dieser
  gestorben ist - genau dann will man ihn aber lesen.
* **System-Python statt venv, nur Standardbibliothek.** So antwortet der Status
  auch waehrend eines laufenden oder fehlgeschlagenen `pip install`, und
  `pyproject.toml` braucht keine zusaetzliche Abhaengigkeit.
* **Dashboard direkt vom Pi ausgeliefert statt separat gehostet.** Kein
  Windows-PC/anderes Geraet muss dafuer laufen; das Dashboard ist verfuegbar,
  solange der Pi an ist, und wird bei jedem Deploy automatisch mit
  aktualisiert (`update.sh` restartet `jarvis-status.service` mit).

Der Endpunkt ist **nicht authentifiziert** und bindet auf `0.0.0.0`. Im LAN ist
das in Ordnung; er gehoert aber nicht per Portfreigabe ins offene Internet
(Hostname, Uptime und Commit-Nachrichten waeren dann oeffentlich lesbar). Fuer
Zugriff von unterwegs stattdessen ein VPN wie Tailscale nutzen - dann bleibt
der Port ungeoeffnet.

`Access-Control-Allow-Origin` ist trotzdem gesetzt - fuer den Fall, dass die
Seite mal von woanders (z.B. `file://` oder einem anderen Host) geladen wird
und cross-origin abfragt.

Pruefen:

```bash
curl -s http://localhost:8090/status | python3 -m json.tool
# oder im Browser: http://<pi-ip>:8090/
```

## systemd-Service (empfohlen fuer den Dauerbetrieb)

```bash
sudo cp deploy/systemd/jarvis.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jarvis.service
```

`Type=notify` + `WatchdogSec=30` nutzen `src/jarvis/watchdog.py` (sd_notify
per Unix-Socket, keine libsystemd-Abhaengigkeit): meldet sich beim Start als
bereit und sendet danach alle 15s ein Lebenszeichen. Bleibt das aus, killt
und startet systemd den Prozess neu (`Restart=always`).

Pfade in `jarvis.service` (`/home/pi/jarvis/...`) ggf. an den echten
Installationsort anpassen.

## Kiosk-Display-Autostart

Voraussetzung: `JARVIS_UI_ENABLED=true` in `.env`, `jarvis.service` laeuft.

```bash
mkdir -p ~/.config/autostart
cp deploy/autostart/jarvis-kiosk.desktop ~/.config/autostart/
```

Startet nach dem naechsten Desktop-Login automatisch Chromium im
Kiosk-Modus gegen `http://127.0.0.1:8000`.

## Docker (Alternative zu systemd+venv)

```bash
docker compose up -d --build
```

Siehe `Dockerfile`/`docker-compose.yml` im Projekt-Root. `.env` wird ueber
`env_file` eingebunden - nicht ins Image backen. Fuer Sprachmodus muss das
Audio-Device in den Container durchgereicht werden (siehe Kommentare in
`docker-compose.yml`).
