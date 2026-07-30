#!/usr/bin/env bash
#
# Erstinstallation von Jarvis auf einem frischen Raspberry Pi 4:
# System-Pakete, Checkout, venv, .env, systemd-Unit und die sudo-Regel, die
# der Auto-Deploy fuer den Service-Neustart braucht.
#
# Aufruf (auf dem Pi):
#   sudo bash deploy/bootstrap-pi.sh
#
# Ist idempotent - ein zweiter Durchlauf aktualisiert nur und loescht nichts.
#
# Konfiguration ueber Umgebungsvariablen:
#   JARVIS_USER     Ziel-Benutzer          (Default: der sudo-Aufrufer)
#   JARVIS_APP_DIR  Installationsverzeichnis (Default: ~/jarvis des Benutzers)
#   JARVIS_BRANCH   Branch                 (Default main)
#   JARVIS_FAN_GPIO GPIO-Pin des Gehaeuse-Luefters, dauerhaft an (Default 10,
#                   leer = keine Luefter-Konfiguration)
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Bitte mit root-Rechten starten: sudo bash deploy/bootstrap-pi.sh" >&2
  exit 1
fi

TARGET_USER="${JARVIS_USER:-${SUDO_USER:-pi}}"
if ! id "$TARGET_USER" >/dev/null 2>&1; then
  echo "Benutzer '$TARGET_USER' existiert nicht. Mit JARVIS_USER=... ueberschreiben." >&2
  exit 1
fi
TARGET_GROUP="$(id -gn "$TARGET_USER")"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

APP_DIR="${JARVIS_APP_DIR:-$TARGET_HOME/jarvis}"
REPO="${JARVIS_REPO:-https://github.com/Hudnur111/Desk-Assistent.git}"
BRANCH="${JARVIS_BRANCH:-main}"
SERVICE=jarvis.service
STATUS_SERVICE=jarvis-status.service
UPDATE_SERVICE=jarvis-update.service
UPDATE_TIMER=jarvis-update.timer
FAN_NEEDS_REBOOT=false

log() { printf '\n[bootstrap] %s\n' "$*"; }
as_user() { runuser -u "$TARGET_USER" -- "$@"; }

log "Benutzer=$TARGET_USER  Verzeichnis=$APP_DIR  Branch=$BRANCH"

log "System-Pakete installieren ..."
export DEBIAN_FRONTEND=noninteractive
apt-get update
# portaudio19-dev/libsndfile1/ffmpeg brauchen sounddevice bzw. faster-whisper.
apt-get install -y --no-install-recommends \
  git curl ca-certificates \
  python3 python3-venv python3-dev \
  build-essential portaudio19-dev libsndfile1 ffmpeg

FAN_GPIO="${JARVIS_FAN_GPIO:-10}"
CONFIG_TXT=/boot/firmware/config.txt
if [[ -n "$FAN_GPIO" && -f "$CONFIG_TXT" ]]; then
  log "Luefter an GPIO$FAN_GPIO dauerhaft einschalten ..."
  # gpio=<pin>=op,dh setzt den Pin schon in der Firmware (vor dem Kernel) als
  # Ausgang auf HIGH - der Luefter geht mit dem Pi an, ohne Kernel-Overlay
  # oder eigenen Dienst. Keine Temperatursteuerung, einfach dauerhaft an.
  FAN_LINE="gpio=$FAN_GPIO=op,dh"
  if ! grep -qxF "$FAN_LINE" "$CONFIG_TXT"; then
    printf '\n# Von deploy/bootstrap-pi.sh: Luefter an GPIO%s fest auf An\n%s\n' \
      "$FAN_GPIO" "$FAN_LINE" >> "$CONFIG_TXT"
    log "config.txt aktualisiert - wird erst nach einem Neustart aktiv."
    FAN_NEEDS_REBOOT=true
  else
    log "Luefter-Konfiguration in config.txt bereits vorhanden."
  fi
fi

log "Repository bereitstellen ..."
if [[ -d "$APP_DIR/.git" ]]; then
  as_user git -C "$APP_DIR" fetch --prune origin "$BRANCH"
  as_user git -C "$APP_DIR" checkout "$BRANCH"
  as_user git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  install -d -o "$TARGET_USER" -g "$TARGET_GROUP" "$APP_DIR"
  as_user git clone --branch "$BRANCH" "$REPO" "$APP_DIR"
fi

# Muss existieren, BEVOR jarvis-status.service startet: die Unit verwendet
# ReadWritePaths=.../data als gezielte Ausnahme von ProtectHome=read-only,
# und dieser Bind-Mount funktioniert nur fuer bereits vorhandene Pfade.
install -d -o "$TARGET_USER" -g "$TARGET_GROUP" "$APP_DIR/data"

UV="$TARGET_HOME/.local/bin/uv"
log "Python 3.11 fuer das venv bereitstellen ..."
# Debian trixie liefert nur Python 3.13 aus - dafuer gibt es kein
# tflite-runtime-Wheel (Google baut es hoechstens bis 3.11), eine
# Hard-Dependency von openwakeword. uv laedt einen fertigen 3.11-Build,
# unabhaengig vom System-Python, statt stundenlang aus Quellcode zu bauen.
if [[ ! -x "$UV" ]]; then
  as_user bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi
as_user "$UV" python install 3.11

log "Python-venv und Abhaengigkeiten (dauert auf dem Pi einige Minuten) ..."
if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
  as_user "$UV" venv --seed --python 3.11 "$APP_DIR/.venv"
fi
as_user "$UV" pip install --python "$APP_DIR/.venv/bin/python" --upgrade -e "$APP_DIR"

env_is_new=false
if [[ ! -f "$APP_DIR/.env" ]]; then
  log ".env aus .env.example anlegen ..."
  as_user cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
  env_is_new=true
else
  log ".env existiert bereits - bleibt unveraendert."
fi

log "systemd-Units installieren ..."
# Die Vorlagen im Repo sind auf /home/pi/jarvis und User=pi verdrahtet - hier
# auf den tatsaechlichen Pfad und Benutzer umschreiben.
for unit in "$SERVICE" "$STATUS_SERVICE" "$UPDATE_SERVICE" "$UPDATE_TIMER"; do
  sed -e "s|/home/pi/jarvis|$APP_DIR|g" \
      -e "s|^User=pi$|User=$TARGET_USER|" \
      -e "s|^Group=pi$|Group=$TARGET_GROUP|" \
      "$APP_DIR/deploy/systemd/$unit" > "/etc/systemd/system/$unit"
done
systemctl daemon-reload
systemctl enable "$SERVICE"

# Der Status-Dienst braucht keinen API-Key und kann sofort laufen - damit
# zeigt das Dashboard den Pi auch dann schon an, wenn Jarvis selbst noch
# nicht konfiguriert ist.
log "Status-Endpunkt starten (Port 8090) ..."
systemctl enable --now "$STATUS_SERVICE"

# Pollt periodisch auf neue Commits - Alternative zum GitHub-Actions-Runner
# (deploy/install-runner.sh), die keinen Registrierungs-Token braucht: das
# Repo ist oeffentlich, git fetch funktioniert ohne Anmeldung. Wer spaeter
# doch den Runner einrichtet, sollte diesen Timer stoppen, um doppelte
# Deploys zu vermeiden (`sudo systemctl disable --now jarvis-update.timer`).
log "Auto-Update-Timer starten (Polling alle 90s) ..."
systemctl enable --now "$UPDATE_TIMER"

log "sudo-Regel fuer Auto-Deploy und Dashboard-Steuerung schreiben ..."
# Erlaubt dem Deploy-/Status-Benutzer ohne Passwort ausschliesslich diese
# konkreten Befehle - kein allgemeines NOPASSWD. Die letzten drei Eintraege
# sind fuer die An/Ruhemodus/Aus-Knoepfe im Dashboard (jarvis-status.service
# ruft sie im Auftrag eines Browser-Klicks auf).
SUDOERS=/etc/sudoers.d/jarvis-deploy
cat > "$SUDOERS" <<EOF
# Von deploy/bootstrap-pi.sh erzeugt.
# Auto-Update (Timer oder GitHub-Actions-Runner): Neustart nach Deploy.
$TARGET_USER ALL=(root) NOPASSWD: /usr/bin/systemctl restart $SERVICE, /bin/systemctl restart $SERVICE, /usr/bin/systemctl restart $STATUS_SERVICE, /bin/systemctl restart $STATUS_SERVICE
# Dashboard-Steuerung (An/Ruhemodus/Aus) - unauthentifiziert erreichbar,
# siehe deploy/README.md fuer die bewusste Risikoabwaegung.
$TARGET_USER ALL=(root) NOPASSWD: /usr/bin/systemctl start $SERVICE, /bin/systemctl start $SERVICE, /usr/bin/systemctl stop $SERVICE, /bin/systemctl stop $SERVICE, /usr/bin/systemctl poweroff, /bin/systemctl poweroff
EOF
chmod 440 "$SUDOERS"
if ! visudo -cf "$SUDOERS" >/dev/null; then
  rm -f "$SUDOERS"
  echo "sudoers-Datei war fehlerhaft und wurde entfernt - Deploy kann den Service nicht neu starten." >&2
  exit 1
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

if [[ "$FAN_NEEDS_REBOOT" == "true" ]]; then
  log "Luefter-Konfiguration braucht einen Neustart, um zu greifen: sudo reboot"
fi

if [[ "$env_is_new" == "true" ]] || ! grep -Eq '^ANTHROPIC_API_KEY=.+' "$APP_DIR/.env"; then
  cat <<EOF

[bootstrap] FERTIG - aber $SERVICE wurde noch NICHT gestartet.
            In $APP_DIR/.env fehlt noch ANTHROPIC_API_KEY.
            Key eintragen, dann starten:

              nano $APP_DIR/.env
              sudo systemctl start $SERVICE
              systemctl status $SERVICE

            Das Dashboard funktioniert schon jetzt:
              http://${IP:-<pi-ip>}:8090/status

EOF
else
  log "Service starten ..."
  systemctl restart "$SERVICE"
  systemctl status "$SERVICE" --no-pager --lines=20 || true
  cat <<EOF

[bootstrap] FERTIG - $SERVICE laeuft.
            Status fuer das Dashboard: http://${IP:-<pi-ip>}:8090/status

EOF
fi
