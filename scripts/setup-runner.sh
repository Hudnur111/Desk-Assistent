#!/usr/bin/env bash
# =============================================================================
# GitHub Actions Self-hosted Runner — Automatisches Setup auf dem Pi
# Voraussetzung: RUNNER_TOKEN muss gesetzt sein (von GitHub Settings)
#
# Verwendung:
#   RUNNER_TOKEN=<token> bash scripts/setup-runner.sh
#
# Token holen:
#   https://github.com/Hudnur111/Desk-Assistent/settings/actions/runners/new
# =============================================================================
set -e

RUNNER_DIR="$HOME/actions-runner"
REPO="https://github.com/Hudnur111/Desk-Assistent"
RUNNER_NAME="${RUNNER_NAME:-pi-$(hostname)}"

if [ -z "$RUNNER_TOKEN" ]; then
  echo "❌ RUNNER_TOKEN fehlt!"
  echo ""
  echo "Hol den Token von:"
  echo "  https://github.com/Hudnur111/Desk-Assistent/settings/actions/runners/new"
  echo ""
  echo "Dann: RUNNER_TOKEN=<token> bash scripts/setup-runner.sh"
  exit 1
fi

echo "📦 GitHub Actions Runner wird eingerichtet..."
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

# Aktuelle Runner-Version ermitteln (ARM64 für Pi 4)
RUNNER_VERSION=$(curl -s https://api.github.com/repos/actions/runner/releases/latest | grep '"tag_name"' | sed 's/.*"v\([^"]*\)".*/\1/')
RUNNER_FILE="actions-runner-linux-arm64-${RUNNER_VERSION}.tar.gz"

if [ ! -f "run.sh" ]; then
  echo "⬇️  Lade Runner v${RUNNER_VERSION}..."
  curl -sL "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${RUNNER_FILE}" \
    -o "$RUNNER_FILE"
  tar xzf "$RUNNER_FILE"
  rm "$RUNNER_FILE"
fi

# Konfigurieren
echo "⚙️  Runner konfigurieren..."
./config.sh \
  --url "$REPO" \
  --token "$RUNNER_TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "self-hosted,Linux,ARM64,raspberry-pi" \
  --unattended \
  --replace

# Als systemd Service installieren
echo "🔧 Runner als systemd Service installieren..."
sudo ./svc.sh install
sudo ./svc.sh start

echo ""
echo "✅ GitHub Actions Runner läuft!"
echo "   Name: $RUNNER_NAME"
echo "   Prüfen: https://github.com/Hudnur111/Desk-Assistent/settings/actions/runners"
echo ""
echo "   Status: sudo ./svc.sh status"
echo "   Logs:   journalctl -u actions.runner.* -f"
