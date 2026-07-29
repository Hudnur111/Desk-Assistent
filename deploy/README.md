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

## Automatischer Deploy bei jedem Push

Ein GitHub-Actions-Self-Hosted-Runner laeuft auf dem Pi selbst. Jeder Push auf
`main` loest damit innerhalb von Sekunden ein Update aus - ohne Portfreigabe,
ohne dass der Pi von aussen erreichbar sein muss (der Runner baut die
Verbindung nach draussen auf).

```bash
bash ~/jarvis/deploy/install-runner.sh
```

Das Skript laedt und entpackt den Runner und gibt dann die drei Befehle aus,
die den Registrierungs-Token brauchen (`config.sh`, `svc.sh install`,
`svc.sh start`) - Token holen unter
`Settings -> Actions -> Runners -> New self-hosted runner`.

Ablauf bei einem Push:

1. `.github/workflows/deploy-pi.yml` startet auf dem Runner (Label `jarvis-pi`).
2. `deploy/update.sh` macht `git fetch` + `reset --hard origin/main` in
   `/home/pi/jarvis`.
3. Hat sich `pyproject.toml` geaendert, laeuft `pip install -e .` nach.
4. `sudo systemctl restart jarvis.service`. Wegen `Type=notify` kehrt der
   Befehl erst zurueck, wenn sich der Dienst als bereit gemeldet hat.
5. Schlaegt der Start fehl, rollt `update.sh` automatisch auf den vorherigen
   Commit zurueck und startet den alten Stand wieder - der Assistent bleibt
   also auch nach einem kaputten Commit lauffaehig. Der Workflow schlaegt dann
   rot fehl.

`.env`, `.venv/` und `data/` stehen in `.gitignore` und werden vom Deploy nie
angefasst. Es laeuft kein `git clean`.

Manuell nachziehen (ohne Push) geht jederzeit:

```bash
bash ~/jarvis/deploy/update.sh
```

Ueber `Actions -> Deploy auf Raspberry Pi -> Run workflow` laesst sich ein
Deploy auch von Hand ausloesen, dort optional mit erzwungener
Neuinstallation der Abhaengigkeiten.

Die sudo-Regel in `/etc/sudoers.d/jarvis-deploy` erlaubt genau einen Befehl
ohne Passwort - `systemctl restart jarvis.service`. Kein allgemeines NOPASSWD.

## Status-Endpunkt fuer das Dashboard

`jarvis-status.service` liefert unter `http://<pi>:8090/status` JSON mit
CPU/RAM/Speicher/Temperatur, Uptime, dem aktuellen Commit und dem Zustand von
`jarvis.service` und des Deploy-Runners. `/health` antwortet nur `ok`, fuer
externe Uptime-Checks.

Zwei Entscheidungen dahinter:

* **Eigener Dienst, nicht Teil von `jarvis.service`.** Ein Monitor, der mit dem
  ueberwachten Prozess zusammen stirbt, kann nicht melden, dass dieser
  gestorben ist - genau dann will man ihn aber lesen.
* **System-Python statt venv, nur Standardbibliothek.** So antwortet der Status
  auch waehrend eines laufenden oder fehlgeschlagenen `pip install`, und
  `pyproject.toml` braucht keine zusaetzliche Abhaengigkeit.

Der Endpunkt ist **nicht authentifiziert** und bindet auf `0.0.0.0`. Im LAN ist
das in Ordnung; er gehoert aber nicht per Portfreigabe ins offene Internet
(Hostname, Uptime und Commit-Nachrichten waeren dann oeffentlich lesbar). Fuer
Zugriff von unterwegs stattdessen ein VPN wie Tailscale nutzen - dann bleibt
der Port ungeoeffnet.

Wichtig: `Access-Control-Allow-Origin` ist gesetzt. Ohne diesen Header
blockiert der Browser die Antwort, weil das Dashboard von einem anderen Origin
geladen wird (`localhost:8765` bzw. `file://`).

Pruefen:

```bash
curl -s http://localhost:8090/status | python3 -m json.tool
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
