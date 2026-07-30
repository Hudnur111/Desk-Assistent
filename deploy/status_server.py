#!/usr/bin/env python3
"""Status-Dashboard und -Endpunkt, direkt vom Pi ausgeliefert.

GET /       liefert das Dashboard (deploy/dashboard/index.html) - von jedem
            Geraet im selben Netz aufrufbar, ohne dass ein anderer Rechner
            laufen muss.
GET /status liefert JSON mit Systemauslastung, dem Zustand von jarvis.service
und dem Deploy-Runner sowie dem aktuell ausgecheckten Commit.
GET /health liefert nur "ok" - fuer Uptime-Checks.

Zwei bewusste Entscheidungen:

* Eigener Dienst, nicht Teil von jarvis.service. Ein Monitor, der mit dem
  ueberwachten Prozess zusammen stirbt, kann nicht melden, dass dieser
  gestorben ist - genau dann will man ihn aber lesen.
* Nur Standardbibliothek, laeuft mit dem System-Python statt im venv. So haengt
  der Status nicht an einem halb fertigen `pip install` waehrend eines Deploys
  und `pyproject.toml` braucht keine zusaetzliche Abhaengigkeit.

Konfiguration ueber Umgebungsvariablen:
  JARVIS_STATUS_PORT    Port                      (Default 8090)
  JARVIS_STATUS_BIND    Bind-Adresse              (Default 0.0.0.0)
  JARVIS_APP_DIR        Checkout fuer die Git-Info (Default /home/denny/jarvis)
  JARVIS_SERVICE        ueberwachte Unit          (Default jarvis.service)
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DASHBOARD_FILE = Path(__file__).parent / "dashboard" / "index.html"

PORT = int(os.environ.get("JARVIS_STATUS_PORT", "8090"))
BIND = os.environ.get("JARVIS_STATUS_BIND", "0.0.0.0")
APP_DIR = os.environ.get("JARVIS_APP_DIR", "/home/denny/jarvis")
SERVICE = os.environ.get("JARVIS_SERVICE", "jarvis.service")

# Das Dashboard wird von localhost bzw. file:// geladen und fragt den Pi
# cross-origin ab - ohne diesen Header blockiert der Browser die Antwort.
CORS_ORIGIN = os.environ.get("JARVIS_STATUS_CORS", "*")


# --------------------------------------------------------------------------
# CPU-Auslastung
# --------------------------------------------------------------------------
class CpuSampler:
    """Misst die CPU-Last im Hintergrund.

    Der Wert muss aus der Differenz zweier /proc/stat-Messungen kommen. Das im
    Request zu tun wuerde jede Antwort um die Messdauer verzoegern - das
    Dashboard bricht nach 4s ab. Also sampelt ein Thread im Takt und der
    Request liest nur den letzten Wert.
    """

    def __init__(self, interval: float = 2.0) -> None:
        self._interval = interval
        self._percent = 0.0
        self._lock = threading.Lock()

    @staticmethod
    def _read() -> tuple[int, int]:
        with open("/proc/stat", encoding="ascii") as fh:
            fields = [int(v) for v in fh.readline().split()[1:]]
        idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
        return sum(fields), idle

    @property
    def percent(self) -> float:
        with self._lock:
            return self._percent

    def run_forever(self) -> None:
        try:
            prev_total, prev_idle = self._read()
        except OSError:
            return
        while True:
            time.sleep(self._interval)
            try:
                total, idle = self._read()
            except OSError:
                continue
            d_total = total - prev_total
            d_idle = idle - prev_idle
            prev_total, prev_idle = total, idle
            if d_total <= 0:
                continue
            with self._lock:
                self._percent = max(0.0, min(100.0, 100.0 * (d_total - d_idle) / d_total))


CPU = CpuSampler()


# --------------------------------------------------------------------------
# Einzelne Messwerte
# --------------------------------------------------------------------------
def read_memory() -> dict:
    values = {}
    try:
        with open("/proc/meminfo", encoding="ascii") as fh:
            for line in fh:
                key, _, rest = line.partition(":")
                if key in ("MemTotal", "MemAvailable"):
                    values[key] = int(rest.split()[0])  # kB
    except OSError:
        return {"percent": 0, "used_mb": 0, "total_mb": 0}

    total_kb = values.get("MemTotal", 0)
    avail_kb = values.get("MemAvailable", 0)
    used_kb = max(0, total_kb - avail_kb)
    return {
        "percent": round(100.0 * used_kb / total_kb, 1) if total_kb else 0,
        "used_mb": round(used_kb / 1024),
        "total_mb": round(total_kb / 1024),
    }


def read_disk(path: str = "/") -> dict:
    try:
        st = os.statvfs(path)
    except OSError:
        return {"percent": 0, "used_gb": 0, "total_gb": 0}
    total = st.f_blocks * st.f_frsize
    # f_bavail (nicht f_bfree): der fuer normale Nutzer verfuegbare Platz,
    # sonst zaehlt die root-Reserve als "frei" und die Prozente stimmen nicht.
    free = st.f_bavail * st.f_frsize
    used = total - free
    gb = 1024 ** 3
    return {
        "percent": round(100.0 * used / total, 1) if total else 0,
        "used_gb": round(used / gb, 1),
        "total_gb": round(total / gb, 1),
    }


def read_temperature() -> float | None:
    for path in (
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/devices/virtual/thermal/thermal_zone0/temp",
    ):
        try:
            with open(path, encoding="ascii") as fh:
                return round(int(fh.read().strip()) / 1000.0, 1)
        except (OSError, ValueError):
            continue
    return None


def read_uptime() -> float:
    try:
        with open("/proc/uptime", encoding="ascii") as fh:
            return float(fh.readline().split()[0])
    except (OSError, ValueError):
        return 0.0


# --------------------------------------------------------------------------
# systemd
# --------------------------------------------------------------------------
def _systemctl(*args: str) -> str:
    try:
        return subprocess.run(
            ("systemctl", *args),
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def service_state(unit: str) -> dict:
    """Zustand einer Unit. Braucht keine root-Rechte."""
    if not unit:
        return {"unit": None, "active": False, "state": "nicht installiert", "uptime_seconds": None}

    out = _systemctl(
        "show", unit,
        "--property=ActiveState",
        "--property=SubState",
        "--property=ActiveEnterTimestampMonotonic",
        "--property=LoadState",
    )
    props = dict(
        line.split("=", 1) for line in out.splitlines() if "=" in line
    )

    if props.get("LoadState") in ("not-found", "masked", None):
        return {"unit": unit, "active": False, "state": "nicht installiert", "uptime_seconds": None}

    active_state = props.get("ActiveState", "unknown")
    sub_state = props.get("SubState", "")

    # Monotone Zeitstempel statt lokalisierter Datumsstrings - locale-unabhaengig.
    uptime_seconds = None
    try:
        entered_us = int(props.get("ActiveEnterTimestampMonotonic", "0"))
        if entered_us > 0:
            uptime_seconds = max(0, round(read_uptime() - entered_us / 1_000_000))
    except ValueError:
        pass

    return {
        "unit": unit,
        "active": active_state == "active",
        "state": f"{active_state} ({sub_state})" if sub_state else active_state,
        "uptime_seconds": uptime_seconds,
    }


_runner_unit_cache: str | None = None


def find_runner_unit() -> str:
    """Unit-Name des GitHub-Actions-Runners.

    Der Name enthaelt Repo und Runner-Namen (actions.runner.<owner>-<repo>.<host>)
    und ist damit nicht vorhersagbar - also einmal suchen und merken.
    """
    global _runner_unit_cache
    if _runner_unit_cache is not None:
        return _runner_unit_cache
    out = _systemctl("list-units", "--type=service", "--all", "--no-legend",
                     "--plain", "actions.runner.*.service")
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0].endswith(".service"):
            _runner_unit_cache = parts[0]
            return _runner_unit_cache
    _runner_unit_cache = ""
    return ""


# --------------------------------------------------------------------------
# Git
# --------------------------------------------------------------------------
def read_git() -> dict:
    def git(*args: str) -> str:
        try:
            res = subprocess.run(
                ("git", "-C", APP_DIR, *args),
                capture_output=True, text=True, timeout=5, check=False,
            )
            return res.stdout.strip() if res.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    return {
        "commit": git("rev-parse", "--short", "HEAD") or "–",
        "message": git("log", "-1", "--format=%s") or "–",
        "branch": git("rev-parse", "--abbrev-ref", "HEAD") or "–",
        "committed_at": git("log", "-1", "--format=%cd", "--date=format:%d.%m.%Y %H:%M") or "–",
    }


def last_deploy() -> str:
    """Zeitpunkt des letzten Deploy-Versuchs.

    .git/FETCH_HEAD wird bei jedem `git fetch` neu geschrieben - und der erste
    Schritt jedes Deploys ist ein fetch. Damit ist die mtime dieser Datei der
    zuverlaessigste Marker fuer "wann lief das Update zuletzt".
    """
    try:
        ts = os.path.getmtime(os.path.join(APP_DIR, ".git", "FETCH_HEAD"))
    except OSError:
        return "–"
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y, %H:%M:%S")


# --------------------------------------------------------------------------
# Payload
# --------------------------------------------------------------------------
def build_status() -> dict:
    jarvis = service_state(SERVICE)
    poll_timer = service_state("jarvis-update.timer")
    runner = service_state(find_runner_unit())
    status_self = service_state("jarvis-status.service")

    # Zwei moegliche Auto-Update-Mechanismen (siehe deploy/README.md):
    # der Polling-Timer (Default, kein Token noetig) oder ein optionaler
    # GitHub-Actions-Runner. Beide rufen update.sh auf - hier wird gemeldet,
    # welcher der beiden tatsaechlich aktiv ist, statt nur den Runner zu
    # pruefen (der im Timer-Betrieb gar nicht installiert ist).
    if poll_timer["active"]:
        update_mechanism = "timer"
    elif runner["active"]:
        update_mechanism = "runner"
    else:
        update_mechanism = None

    return {
        "hostname": socket.gethostname(),
        "server_time": datetime.now().strftime("%d.%m.%Y, %H:%M:%S"),
        "cpu_percent": round(CPU.percent, 1),
        "cpu_cores": os.cpu_count() or 1,
        "memory": read_memory(),
        "disk": read_disk(),
        "temperature_c": read_temperature(),
        "uptime_seconds": round(read_uptime()),
        "git": read_git(),
        "update_timer": {
            "active": update_mechanism is not None,
            "mechanism": update_mechanism,
            "last_run": last_deploy(),
        },
        "services": {
            "jarvis": jarvis,
            "poll_timer": poll_timer,
            "runner": runner,
            "status": status_self,
        },
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "JarvisStatus/1.0"

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path == "/":
            try:
                body = DASHBOARD_FILE.read_bytes()
            except OSError:
                self._send(404, b"Dashboard-Datei fehlt.", "text/plain; charset=utf-8")
                return
            self._send(200, body, "text/html; charset=utf-8")
        elif path == "/status":
            body = json.dumps(build_status(), ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        elif path == "/health":
            self._send(200, b"ok\n", "text/plain; charset=utf-8")
        else:
            self._send(404, b'{"error":"not found"}', "application/json")

    def log_message(self, fmt: str, *args) -> None:
        """Kein Request-Log.

        Das Dashboard pollt alle 3 Sekunden - das waeren ~28800 Zeilen pro Tag
        im journal, ohne jeden Informationsgewinn.
        """
        return


def main() -> None:
    threading.Thread(target=CPU.run_forever, daemon=True).start()
    server = ThreadingHTTPServer((BIND, PORT), Handler)
    server.daemon_threads = True
    print(f"[status] hoert auf http://{BIND}:{PORT}/status (App: {APP_DIR})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
