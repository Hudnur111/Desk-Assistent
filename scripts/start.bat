@echo off
title Desk Assistant
color 0B

echo.
echo  ====================================
echo   DESK ASSISTANT - AI Desktop Client
echo   Ollama + Claude / Raspberry Pi 4B
echo  ====================================
echo.

:: Check Node.js
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org
    pause
    exit /b 1
)

:: Go to app root (one level up from scripts/)
cd /d "%~dp0.."

:: Install dependencies if node_modules missing
if not exist "node_modules" (
    echo [SETUP] Installing dependencies...
    call npm install --silent
)

:: Build if .next missing
if not exist ".next" (
    echo [BUILD] Building Next.js app...
    call npm run build
)

:: Start server in background
echo [START] Starting Desk Assistant on port 3000...
start /B npm run start

:: Wait for server
timeout /t 3 /nobreak >nul

:: Open browser
echo [OPEN] Opening browser...
start "" "http://localhost:3000"

echo.
echo  Server running at http://localhost:3000
echo  Press Ctrl+C to stop.
echo.

:: Keep window open to show logs
npm run start
