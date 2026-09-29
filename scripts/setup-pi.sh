#!/usr/bin/env bash
# =============================================================================
# Desk Assistant — Raspberry Pi 4B Vollinstallation
# Führe dieses Script EINMALIG auf dem Pi aus:
#   curl -fsSL https://raw.githubusercontent.com/Hudnur111/Desk-Assistent/main/scripts/setup-pi.sh | bash
# =============================================================================
set -e

REPO_URL="https://github.com/Hudnur111/Desk-Assistent.git"
APP_DIR="$HOME/Desk-Assistent"
SERVICE_NAME="desk-assistant"
RUNNER_DIR="$HOME/actions-runner"
PORT="${PORT:-3000}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log() { echo -e "${BLUE}[SETUP]${NC} $1"; }
ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn(){ echo -e "${YELLOW}[WARN]${NC} $1"; }

echo ""
echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Desk Assistant — Pi 4B Setup       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# ── 1. System-Pakete ────────────────────────────────────────────────────────
log "System-Pakete aktualisieren..."
sudo apt-get update -qq
sudo apt-get install -y -qq git curl wget nodejs npm chromium-browser

# Node.js >= 18 benötigt
NODE_VER=$(node -e "process.exit(parseInt(process.version.slice(1)) < 18 ? 1 : 0)" 2>/dev/null && echo "ok" || echo "old")
if [ "$NODE_VER" = "old" ]; then
  log "Node.js upgraden (>= 18)..."
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
ok "Node.js $(node --version)"

# ── 2. Ollama installieren ───────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
  log "Ollama installieren..."
  curl -fsSL https://ollama.com/install.sh | sh
  ok "Ollama installiert"
else
  ok "Ollama bereits vorhanden ($(ollama --version 2>/dev/null || echo 'ok'))"
fi

# Ollama-Modell ziehen (llama3.2 ~2GB, optional)
log "Ollama-Modell llama3.2 laden (kann einige Minuten dauern)..."
ollama pull llama3.2 || warn "Modell konnte nicht geladen werden — später nachholen mit: ollama pull llama3.2"

# ── 3. App klonen / aktualisieren ───────────────────────────────────────────
if [ -d "$APP_DIR/.git" ]; then
  log "Repo aktualisieren..."
  git -C "$APP_DIR" pull --ff-only origin main
else
  log "Repo klonen..."
  git clone "$REPO_URL" "$APP_DIR"
fi
ok "Repo: $APP_DIR"

# ── 4. Abhängigkeiten & Build ────────────────────────────────────────────────
log "npm install..."
npm --prefix "$APP_DIR" ci 2>/dev/null || npm --prefix "$APP_DIR" install

log "Next.js bauen..."
npm --prefix "$APP_DIR" run build
ok "Build fertig"

# ── 5. systemd Service ───────────────────────────────────────────────────────
log "systemd Service einrichten..."
cat | sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<SERVICE
[Unit]
Description=Desk Assistant AI (Next.js)
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=NODE_ENV=production
Environment=PORT=$PORT
ExecStart=/usr/bin/node node_modules/.bin/next start -p $PORT
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.service
sudo systemctl restart ${SERVICE_NAME}.service
sleep 2
systemctl is-active --quiet ${SERVICE_NAME}.service && ok "Service läuft auf Port $PORT" || warn "Service-Start fehlgeschlagen — prüfe: journalctl -u ${SERVICE_NAME}"

# ── 6. GitHub Actions Runner ─────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  GitHub Actions Self-hosted Runner einrichten${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  1. Gehe zu: https://github.com/Hudnur111/Desk-Assistent/settings/actions/runners/new"
echo "  2. Wähle: Linux / ARM64"
echo "  3. Kopiere den Download-Befehl und den ./config.sh-Befehl"
echo "  4. Führe dann aus:"
echo ""
echo "     mkdir -p $RUNNER_DIR && cd $RUNNER_DIR"
echo "     # (Download + config Befehle von GitHub einfügen)"
echo "     ./run.sh &  # oder als Service: ./svc.sh install && ./svc.sh start"
echo ""
echo -e "${YELLOW}  Script: scripts/setup-runner.sh (automatisiert Schritt 3-4)${NC}"
echo ""

# ── 7. Autostart Chromium ────────────────────────────────────────────────────
log "Chromium Autostart konfigurieren..."
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/desk-assistant.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Desk Assistant
Comment=AI Desktop Client
Exec=bash -c "sleep 5 && chromium-browser --app=http://localhost:$PORT --kiosk"
X-GNOME-Autostart-enabled=true
DESKTOP
ok "Chromium öffnet http://localhost:$PORT beim Desktop-Login"

# ── Fertig ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Installation abgeschlossen!           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "  App:      http://localhost:$PORT"
echo "  Service:  systemctl status $SERVICE_NAME"
echo "  Logs:     journalctl -u $SERVICE_NAME -f"
echo "  Neustart: sudo systemctl restart $SERVICE_NAME"
echo ""
