import asyncio
import socket
from pathlib import Path

import pytest

from jarvis import watchdog


@pytest.mark.asyncio
async def test_notify_ready_sends_ready_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    socket_path = str(tmp_path / "notify.sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(socket_path)
    server.settimeout(2)
    monkeypatch.setenv("NOTIFY_SOCKET", socket_path)
    try:
        await watchdog.notify_ready()
        data, _ = server.recvfrom(1024)
        assert data == b"READY=1"
    finally:
        server.close()


def test_notify_without_socket_env_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    watchdog._notify("READY=1")


@pytest.mark.asyncio
async def test_watchdog_heartbeat_sends_repeated_messages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    socket_path = str(tmp_path / "notify.sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(socket_path)
    server.settimeout(2)
    monkeypatch.setenv("NOTIFY_SOCKET", socket_path)

    task = asyncio.create_task(watchdog.run_watchdog_heartbeat(interval_seconds=0.01))
    try:
        # recvfrom blockiert synchron - in einen Thread auslagern, damit der
        # Event-Loop parallel den Heartbeat-Task weiterlaufen lassen kann.
        received = [
            (await asyncio.to_thread(server.recvfrom, 1024))[0] for _ in range(3)
        ]
    finally:
        task.cancel()
        server.close()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert received == [b"WATCHDOG=1"] * 3
