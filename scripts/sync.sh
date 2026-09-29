#!/usr/bin/env bash
# GitHub Sync Script — pulls latest from main
set -e
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

echo "[SYNC] Fetching latest from GitHub..."
git fetch origin main
git pull --ff-only origin main

echo "[SYNC] Checking for dependency updates..."
npm install --silent

echo "[SYNC] Rebuilding..."
npm run build

echo "[SYNC] Done! Restart the app to apply changes."
