"""Tests fuer deploy/status_server.py.

Kein Package unter src/ (bewusst: laeuft mit dem System-Python auf dem Pi,
siehe Modul-Docstring), daher per importlib.util direkt aus dem Pfad geladen
statt per normalem Import.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_STATUS_SERVER_PATH = Path(__file__).resolve().parents[1] / "deploy" / "status_server.py"
_spec = importlib.util.spec_from_file_location("status_server", _STATUS_SERVER_PATH)
assert _spec is not None and _spec.loader is not None
status_server = importlib.util.module_from_spec(_spec)
sys.modules["status_server"] = status_server
_spec.loader.exec_module(status_server)


def test_read_disk_computes_percent_from_available_not_free(tmp_path: Path) -> None:
    result = status_server.read_disk(str(tmp_path))
    assert 0 <= result["percent"] <= 100
    assert result["total_gb"] >= 0


def test_read_disk_missing_path_returns_zeroed_dict() -> None:
    result = status_server.read_disk("/this/path/does/not/exist/at/all")
    assert result == {"percent": 0, "used_gb": 0, "total_gb": 0}


def test_log_and_read_control_history_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_file = tmp_path / "data" / "control-history.jsonl"
    monkeypatch.setattr(status_server, "CONTROL_HISTORY_FILE", str(history_file))

    status_server.log_control_action("start", True)
    status_server.log_control_action("shutdown", False)

    entries = status_server.read_control_history()
    # Neuestes zuerst.
    assert [e["action"] for e in entries] == ["shutdown", "start"]
    assert entries[0]["ok"] is False
    assert entries[1]["ok"] is True
    assert "ts" in entries[0]


def test_read_control_history_missing_file_returns_empty_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(status_server, "CONTROL_HISTORY_FILE", str(tmp_path / "missing.jsonl"))
    assert status_server.read_control_history() == []


def test_read_control_history_respects_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_file = tmp_path / "control-history.jsonl"
    monkeypatch.setattr(status_server, "CONTROL_HISTORY_FILE", str(history_file))
    for i in range(10):
        status_server.log_control_action(f"action{i}", True)

    entries = status_server.read_control_history(limit=3)
    assert len(entries) == 3
    assert entries[0]["action"] == "action9"


def test_read_deploy_history_reverses_and_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_file = tmp_path / "deploy-history.jsonl"
    monkeypatch.setattr(status_server, "DEPLOY_HISTORY_FILE", str(history_file))
    with open(history_file, "w", encoding="utf-8") as fh:
        for i in range(5):
            fh.write(json.dumps({"ts": f"t{i}", "from": "a", "to": "b", "outcome": "deployed"}) + "\n")

    entries = status_server.read_deploy_history(limit=2)
    assert [e["ts"] for e in entries] == ["t4", "t3"]


def test_read_deploy_history_skips_malformed_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    history_file = tmp_path / "deploy-history.jsonl"
    monkeypatch.setattr(status_server, "DEPLOY_HISTORY_FILE", str(history_file))
    history_file.write_text('{"ts": "t1"}\nnot json\n{"ts": "t2"}\n', encoding="utf-8")

    entries = status_server.read_deploy_history()
    assert [e["ts"] for e in entries] == ["t2", "t1"]


def test_service_state_reports_not_installed_for_missing_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(status_server, "_systemctl", lambda *a: "LoadState=not-found\n")
    result = status_server.service_state("nonexistent.service")
    assert result["active"] is False
    assert result["state"] == "nicht installiert"
    assert result["uptime_seconds"] is None


def test_service_state_reports_active_with_uptime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        status_server,
        "_systemctl",
        lambda *a: (
            "ActiveState=active\n"
            "SubState=running\n"
            "ActiveEnterTimestampMonotonic=1000000\n"
            "LoadState=loaded\n"
        ),
    )
    monkeypatch.setattr(status_server, "read_uptime", lambda: 61.0)
    result = status_server.service_state("jarvis.service")
    assert result["active"] is True
    assert result["state"] == "active (running)"
    assert result["uptime_seconds"] == 60


def test_service_state_empty_unit_name_is_not_installed() -> None:
    result = status_server.service_state("")
    assert result == {"unit": None, "active": False, "state": "nicht installiert", "uptime_seconds": None}


def test_service_restart_count_parses_nrestarts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(status_server, "_systemctl", lambda *a: "NRestarts=7\n")
    assert status_server.service_restart_count("jarvis.service") == 7


def test_service_restart_count_missing_property_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(status_server, "_systemctl", lambda *a: "")
    assert status_server.service_restart_count("jarvis.service") is None


def test_run_control_action_rejects_unknown_action() -> None:
    ok, message = status_server.run_control_action("reboot-into-bios")
    assert ok is False
    assert "unbekannte Aktion" in message


def test_run_control_action_success_logs_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(status_server, "CONTROL_HISTORY_FILE", str(tmp_path / "history.jsonl"))
    monkeypatch.setattr(
        status_server.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a, 0, stdout="", stderr=""),
    )
    ok, message = status_server.run_control_action("start")
    assert ok is True
    assert message == "OK"
    assert status_server.read_control_history()[0]["action"] == "start"


def test_run_control_action_failure_reports_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(status_server, "CONTROL_HISTORY_FILE", str(tmp_path / "history.jsonl"))
    monkeypatch.setattr(
        status_server.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a, 1, stdout="", stderr="nicht erlaubt"),
    )
    ok, message = status_server.run_control_action("shutdown")
    assert ok is False
    assert message == "nicht erlaubt"
    assert status_server.read_control_history()[0]["ok"] is False
