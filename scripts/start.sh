#!/usr/bin/env bash
# Desk Assistant — Raspberry Pi 4B Launcher
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
PORT="${PORT:-3000}"

echo ""
echo "  ======================================"
echo "   DESK ASSISTANT — AI Desktop Client"
echo "   Ollama + Claude / Raspberry Pi 4B"
echo "  ======================================"
echo ""

cd "$APP_DIR"

# Install deps if needed
if [ ! -d "node_modules" ]; then
  echo "[SETUP] Installing dependencies..."
  npm install --silent
fi

# Build if needed
if [ ! -d ".next" ]; then
  echo "[BUILD] Building Next.js app..."
  npm run build
fi

# Start Ollama if installed and not running
if command -v ollama &>/dev/null; then
  if ! pgrep -x ollama >/dev/null; then
    echo "[OLLAMA] Starting Ollama..."
    ollama serve &>/tmp/ollama.log &
    sleep 2
  else
    echo "[OLLAMA] Already running."
  fi
fi

echo "[START] Starting Desk Assistant on port $PORT..."
export PORT="$PORT"
npm run start &
SERVER_PID=$!

sleep 2

# Open browser (Raspberry Pi: chromium-browser or chromium)
echo "[OPEN] Opening browser..."
if command -v chromium-browser &>/dev/null; then
  chromium-browser --app="http://localhost:$PORT" --kiosk &
elif command -v chromium &>/dev/null; then
  chromium --app="http://localhost:$PORT" &
elif command -v xdg-open &>/dev/null; then
  xdg-open "http://localhost:$PORT" &
fi

echo ""
echo "  Server: http://localhost:$PORT"
echo "  PID: $SERVER_PID"
echo "  Press Ctrl+C to stop."
echo ""

wait $SERVER_PID
