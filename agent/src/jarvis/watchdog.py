import asyncio
import os
import socket


def _notify(message: str) -> None:
    # sd_notify-Protokoll direkt per Unix-Datagram-Socket implementiert, um
    # keine libsystemd-Abhaengigkeit auf dem Pi zu brauchen. Ohne
    # NOTIFY_SOCKET (kein systemd Type=notify) ein No-Op.
    address = os.environ.get("NOTIFY_SOCKET")
    if not address:
        return
    if address.startswith("@"):
        address = "\0" + address[1:]

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sock.connect(address)
        sock.sendall(message.encode("utf-8"))
    finally:
        sock.close()


async def notify_ready() -> None:
    await asyncio.to_thread(_notify, "READY=1")


async def run_watchdog_heartbeat(interval_seconds: float = 15.0) -> None:
    # Haelt systemds WatchdogSec zufrieden; bleibt das hier aus, killt und
    # restartet systemd den Prozess (Restart=always).
    while True:
        await asyncio.to_thread(_notify, "WATCHDOG=1")
        await asyncio.sleep(interval_seconds)
