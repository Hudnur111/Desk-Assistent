#!/usr/bin/env bash
#
# Laedt den GitHub-Actions-Self-Hosted-Runner auf den Pi und macht ihn
# startklar. Der Registrierungs-Token wird von diesem Skript absichtlich NICHT
# entgegengenommen - die drei Befehle, die ihn brauchen, werden am Ende
# ausgegeben und von dir selbst eingegeben.
#
# Aufruf (auf dem Pi, als normaler Benutzer, NICHT als root):
#   bash deploy/install-runner.sh
set -euo pipefail

RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner}"
REPO_URL="${REPO_URL:-https://github.com/Hudnur111/Desk-Assistent}"
RUNNER_LABELS="${RUNNER_LABELS:-jarvis-pi}"
RUNNER_NAME="${RUNNER_NAME:-$(hostname)}"
FALLBACK_VERSION=2.328.0

log() { printf '\n[runner] %s\n' "$*"; }

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Bitte NICHT als root starten - der Runner soll als normaler Benutzer laufen." >&2
  exit 1
fi

case "$(uname -m)" in
  aarch64|arm64)
    RUNNER_ARCH=arm64
    ;;
  armv7l|armv6l)
    cat >&2 <<'EOF'
Dieser Pi laeuft mit einem 32-bit-System. Der Runner braucht fuer die
Actions-Schritte (actions/checkout) eine Node.js-Runtime, die es fuer 32-bit-ARM
nicht mehr gibt. Bitte Raspberry Pi OS 64-bit installieren - der Pi 4 kann das.
EOF
    exit 1
    ;;
  *)
    echo "Nicht unterstuetzte Architektur: $(uname -m)" >&2
    exit 1
    ;;
esac

log "Neueste Runner-Version ermitteln ..."
VERSION="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest \
  | sed -n 's/.*"tag_name": *"v\([^"]*\)".*/\1/p' | head -n1)"
if [[ -z "$VERSION" ]]; then
  VERSION="$FALLBACK_VERSION"
  log "GitHub-API nicht erreichbar - nutze Fallback-Version $VERSION."
fi
log "Version $VERSION, Architektur $RUNNER_ARCH"

TARBALL="actions-runner-linux-${RUNNER_ARCH}-${VERSION}.tar.gz"
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

if [[ -x ./config.sh ]]; then
  log "Runner ist in $RUNNER_DIR schon entpackt - Download uebersprungen."
else
  log "Runner herunterladen ..."
  curl -fSL -o "$TARBALL" \
    "https://github.com/actions/runner/releases/download/v${VERSION}/${TARBALL}"
  tar xzf "$TARBALL"
  rm -f "$TARBALL"
fi

log "System-Abhaengigkeiten des Runners installieren (fragt nach sudo) ..."
sudo ./bin/installdependencies.sh

cat <<EOF

============================================================================
[runner] Download fertig. Jetzt sind noch drei Befehle von dir dran - der
         Registrierungs-Token gehoert in deine Haende, nicht in ein Skript.

1) Token holen:
   $REPO_URL/settings/actions/runners/new
   -> Linux / ARM64 auswaehlen, den Wert hinter --token kopieren.
   (Der Token ist nur ca. 1 Stunde gueltig.)

2) Auf dem Pi registrieren - DEIN_TOKEN ersetzen:

   cd $RUNNER_DIR
   ./config.sh --url $REPO_URL --token DEIN_TOKEN \\
     --name "$RUNNER_NAME" --labels $RUNNER_LABELS --unattended --replace

3) Als Dienst einrichten, damit er Reboots ueberlebt:

   sudo ./svc.sh install $USER
   sudo ./svc.sh start
   sudo ./svc.sh status

Danach steht der Runner unter $REPO_URL/settings/actions/runners
auf "Idle" und jeder Push auf main deployt automatisch.

WICHTIG: Das Label "$RUNNER_LABELS" muss so bleiben - der Workflow
.github/workflows/deploy-pi.yml sucht den Runner darueber.
============================================================================

EOF
