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
#   JARVIS_APP_DIR         Installationsverzeichnis (Default /home/denny/jarvis)
#   JARVIS_BRANCH          Branch                   (Default main)
#   JARVIS_SERVICE         systemd-Unit             (Default jarvis.service)
#   JARVIS_STATUS_SERVICE  Status-Unit       (Default jarvis-status.service)
#   JARVIS_FORCE_DEPS      "true" = pip-Install erzwingen
set -euo pipefail

APP_DIR="${JARVIS_APP_DIR:-/home/denny/jarvis}"
BRANCH="${JARVIS_BRANCH:-main}"
SERVICE="${JARVIS_SERVICE:-jarvis.service}"
STATUS_SERVICE="${JARVIS_STATUS_SERVICE:-jarvis-status.service}"
FORCE_DEPS="${JARVIS_FORCE_DEPS:-false}"

PIP="$APP_DIR/.venv/bin/pip"

log() { printf '[update] %s\n' "$*"; }
die() { printf '[update] FEHLER: %s\n' "$*" >&2; exit 1; }

deps_hash() { sha256sum "$APP_DIR/pyproject.toml" | cut -d' ' -f1; }

HISTORY_FILE="$APP_DIR/data/deploy-history.jsonl"

# Verlauf fuers Dashboard. Nur echte Deploy-Versuche (nicht jeder "schon
# aktuell"-Check alle 90s, sonst Log-Spam). Felder sind alle selbst erzeugt
# (Zeitstempel, feste outcome-Werte, Commit-SHAs) - kein Escaping fuer
# Freitext noetig, printf reicht.
log_history() {
  local outcome="$1" from_commit="$2" to_commit="$3"
  mkdir -p "$(dirname "$HISTORY_FILE")"
  printf '{"ts":"%s","outcome":"%s","from":"%s","to":"%s"}\n' \
    "$(date -Iseconds)" "$outcome" "${from_commit:0:7}" "${to_commit:0:7}" >> "$HISTORY_FILE"
  # Verlauf klein halten - nur die letzten 50 Eintraege.
  tail -n 50 "$HISTORY_FILE" > "$HISTORY_FILE.tmp" && mv "$HISTORY_FILE.tmp" "$HISTORY_FILE"
}

[[ -d "$APP_DIR/.git" ]] || die "$APP_DIR ist kein git-Checkout. Erst deploy/bootstrap-pi.sh ausfuehren."
[[ -x "$PIP" ]] || die "Kein venv unter $APP_DIR/.venv. Erst deploy/bootstrap-pi.sh ausfuehren."

cd "$APP_DIR"

previous_commit="$(git rev-parse HEAD)"
previous_deps="$(deps_hash)"
deps_reinstalled=false

# Muss VOR dem Update erfasst werden: war $SERVICE schon vorher nicht aktiv
# (z.B. weil ANTHROPIC_API_KEY noch fehlt), ist ein weiterhin fehlgeschlagener
# Start danach keine Regression durch dieses Update - dann gibt es nichts,
# worauf zurueckgerollt werden muesste. Sonst wuerde ein voellig gutes
# Code-Update wegen eines laengst bekannten Konfigurationsproblems
# zurueckgedreht.
service_was_active=false
if systemctl is-active --quiet "$SERVICE"; then
  service_was_active=true
fi

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

# Der Status-Dienst liegt mit im Repo, muss also auch neu geladen werden.
# Bewusst VOR dem Hauptdienst und ohne Rollback-Kopplung: er ist nur ein
# Monitor - faellt er aus, ist das kein Grund, ein gutes Update zurueckzudrehen.
if systemctl list-unit-files "$STATUS_SERVICE" --no-legend --plain 2>/dev/null | grep -q .; then
  log "Starte $STATUS_SERVICE neu ..."
  sudo -n systemctl restart "$STATUS_SERVICE" \
    || log "WARNUNG: $STATUS_SERVICE liess sich nicht neu starten - Dashboard evtl. offline."
fi

log "Starte $SERVICE neu ..."
# Type=notify: systemctl restart kehrt erst zurueck, wenn der Dienst sich als
# bereit gemeldet hat - ein Erfolg hier heisst also wirklich "laeuft".
if sudo -n systemctl restart "$SERVICE" && systemctl is-active --quiet "$SERVICE"; then
  log "OK - $SERVICE laeuft auf ${target_commit:0:7}."
  log_history "deployed" "$previous_commit" "$target_commit"
  exit 0
fi

if [[ "$service_was_active" == "false" ]]; then
  log "$SERVICE lief schon vor dem Update nicht (z.B. fehlender ANTHROPIC_API_KEY) -"
  log "kein Rollback, das ist keine Regression durch dieses Update. Code-Stand ${target_commit:0:7} bleibt."
  log_history "deployed_service_down" "$previous_commit" "$target_commit"
  exit 0
fi

log "Neustart fehlgeschlagen (lief vorher einwandfrei). Rollback auf ${previous_commit:0:7} ..."
log "Falls sudo nach einem Passwort gefragt hat, fehlt /etc/sudoers.d/jarvis-deploy (siehe deploy/bootstrap-pi.sh)."
log_history "rolled_back" "$previous_commit" "$target_commit"
git reset --hard "$previous_commit"
if [[ "$deps_reinstalled" == "true" ]]; then
  "$PIP" install --upgrade -e . || log "WARNUNG: pip-Install beim Rollback fehlgeschlagen."
fi
sudo -n systemctl restart "$SERVICE" || log "WARNUNG: Auch der Rollback-Neustart schlug fehl - manuell pruefen."
die "Deploy abgebrochen, Stand ${previous_commit:0:7} wiederhergestellt."
