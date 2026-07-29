#!/usr/bin/env bash
#
# Zieht origin/<branch> in die Pi-Installation, installiert bei Bedarf
# Abhaengigkeiten nach und startet den systemd-Service neu. Schlaegt der
# Neustart fehl, wird automatisch auf den vorherigen Commit zurueckgerollt,
# damit der Assistent nicht kaputt stehen bleibt.
#
# Aufruf durch .github/workflows/deploy-pi.yml, funktioniert aber auch manuell:
#   bash deploy/update.sh
#
# Konfiguration ueber Umgebungsvariablen:
#   JARVIS_APP_DIR     Installationsverzeichnis   (Default /home/pi/jarvis)
#   JARVIS_BRANCH      Branch                     (Default main)
#   JARVIS_SERVICE     systemd-Unit               (Default jarvis.service)
#   JARVIS_FORCE_DEPS  "true" = pip-Install erzwingen
set -euo pipefail

APP_DIR="${JARVIS_APP_DIR:-/home/pi/jarvis}"
BRANCH="${JARVIS_BRANCH:-main}"
SERVICE="${JARVIS_SERVICE:-jarvis.service}"
FORCE_DEPS="${JARVIS_FORCE_DEPS:-false}"

PIP="$APP_DIR/.venv/bin/pip"

log() { printf '[update] %s\n' "$*"; }
die() { printf '[update] FEHLER: %s\n' "$*" >&2; exit 1; }

deps_hash() { sha256sum "$APP_DIR/pyproject.toml" | cut -d' ' -f1; }

[[ -d "$APP_DIR/.git" ]] || die "$APP_DIR ist kein git-Checkout. Erst deploy/bootstrap-pi.sh ausfuehren."
[[ -x "$PIP" ]] || die "Kein venv unter $APP_DIR/.venv. Erst deploy/bootstrap-pi.sh ausfuehren."

cd "$APP_DIR"

previous_commit="$(git rev-parse HEAD)"
previous_deps="$(deps_hash)"
deps_reinstalled=false

log "Hole origin/$BRANCH ..."
git fetch --prune origin "$BRANCH"
target_commit="$(git rev-parse "origin/$BRANCH")"

if [[ "$previous_commit" == "$target_commit" ]]; then
  log "Schon aktuell (${previous_commit:0:7}) - nichts zu tun."
  exit 0
fi

log "Update ${previous_commit:0:7} -> ${target_commit:0:7}"
# .env, .venv/ und data/ stehen in .gitignore und werden von reset --hard
# nicht angetastet. Kein git clean - das wuerde lokale Daten loeschen.
git reset --hard "$target_commit"

if [[ "$FORCE_DEPS" == "true" || "$previous_deps" != "$(deps_hash)" ]]; then
  log "Abhaengigkeiten werden nachgezogen (kann auf dem Pi einige Minuten dauern) ..."
  "$PIP" install --upgrade -e .
  deps_reinstalled=true
else
  log "pyproject.toml unveraendert - pip-Install uebersprungen."
fi

log "Starte $SERVICE neu ..."
# Type=notify: systemctl restart kehrt erst zurueck, wenn der Dienst sich als
# bereit gemeldet hat - ein Erfolg hier heisst also wirklich "laeuft".
if sudo -n systemctl restart "$SERVICE" && systemctl is-active --quiet "$SERVICE"; then
  log "OK - $SERVICE laeuft auf ${target_commit:0:7}."
  exit 0
fi

log "Neustart fehlgeschlagen. Rollback auf ${previous_commit:0:7} ..."
log "Falls sudo nach einem Passwort gefragt hat, fehlt /etc/sudoers.d/jarvis-deploy (siehe deploy/bootstrap-pi.sh)."
git reset --hard "$previous_commit"
if [[ "$deps_reinstalled" == "true" ]]; then
  "$PIP" install --upgrade -e . || log "WARNUNG: pip-Install beim Rollback fehlgeschlagen."
fi
sudo -n systemctl restart "$SERVICE" || log "WARNUNG: Auch der Rollback-Neustart schlug fehl - manuell pruefen."
die "Deploy abgebrochen, Stand ${previous_commit:0:7} wiederhergestellt."
