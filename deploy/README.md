# Deployment auf dem Raspberry Pi 4

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
