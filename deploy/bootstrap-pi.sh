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

log "Repository bereitstellen ..."
if [[ -d "$APP_DIR/.git" ]]; then
  as_user git -C "$APP_DIR" fetch --prune origin "$BRANCH"
  as_user git -C "$APP_DIR" checkout "$BRANCH"
  as_user git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  install -d -o "$TARGET_USER" -g "$TARGET_GROUP" "$APP_DIR"
  as_user git clone --branch "$BRANCH" "$REPO" "$APP_DIR"
fi

log "Python-venv und Abhaengigkeiten (dauert auf dem Pi einige Minuten) ..."
if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
  as_user python3 -m venv "$APP_DIR/.venv"
fi
as_user "$APP_DIR/.venv/bin/pip" install --upgrade pip setuptools wheel
as_user "$APP_DIR/.venv/bin/pip" install --upgrade -e "$APP_DIR"

env_is_new=false
if [[ ! -f "$APP_DIR/.env" ]]; then
  log ".env aus .env.example anlegen ..."
  as_user cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
  env_is_new=true
else
  log ".env existiert bereits - bleibt unveraendert."
fi

log "systemd-Unit installieren ..."
# Die Vorlage im Repo ist auf /home/pi/jarvis und User=pi verdrahtet - hier
# auf den tatsaechlichen Pfad und Benutzer umschreiben.
sed -e "s|/home/pi/jarvis|$APP_DIR|g" \
    -e "s|^User=pi$|User=$TARGET_USER|" \
    -e "s|^Group=pi$|Group=$TARGET_GROUP|" \
    "$APP_DIR/deploy/systemd/$SERVICE" > "/etc/systemd/system/$SERVICE"
systemctl daemon-reload
systemctl enable "$SERVICE"

log "sudo-Regel fuer den Auto-Deploy schreiben ..."
# Erlaubt dem Deploy-Benutzer genau einen Befehl ohne Passwort: den Neustart
# dieser einen Unit. Kein allgemeines NOPASSWD.
SUDOERS=/etc/sudoers.d/jarvis-deploy
cat > "$SUDOERS" <<EOF
# Von deploy/bootstrap-pi.sh erzeugt - erlaubt dem GitHub-Actions-Runner,
# ausschliesslich $SERVICE neu zu starten.
$TARGET_USER ALL=(root) NOPASSWD: /usr/bin/systemctl restart $SERVICE, /bin/systemctl restart $SERVICE
EOF
chmod 440 "$SUDOERS"
if ! visudo -cf "$SUDOERS" >/dev/null; then
  rm -f "$SUDOERS"
  echo "sudoers-Datei war fehlerhaft und wurde entfernt - Deploy kann den Service nicht neu starten." >&2
  exit 1
fi

if [[ "$env_is_new" == "true" ]] || ! grep -Eq '^ANTHROPIC_API_KEY=.+' "$APP_DIR/.env"; then
  cat <<EOF

[bootstrap] FERTIG - aber der Service wurde noch NICHT gestartet.
            In $APP_DIR/.env fehlt noch ANTHROPIC_API_KEY.
            Key eintragen, dann starten:

              nano $APP_DIR/.env
              sudo systemctl start $SERVICE
              systemctl status $SERVICE

EOF
else
  log "Service starten ..."
  systemctl restart "$SERVICE"
  systemctl status "$SERVICE" --no-pager --lines=20 || true
  log "FERTIG - $SERVICE laeuft."
fi
