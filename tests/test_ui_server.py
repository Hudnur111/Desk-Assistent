import asyncio
import json
import time

from fastapi.testclient import TestClient

from jarvis.ui.hub import UIHub
from jarvis.ui.server import create_app


def _wait_until(predicate, timeout: float = 1.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_index_serves_html() -> None:
    client = TestClient(create_app(UIHub()))
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "J.A.R.V.I.S." in response.text


def test_static_assets_are_served() -> None:
    client = TestClient(create_app(UIHub()))
    css = client.get("/static/style.css")
    js = client.get("/static/app.js")
    assert css.status_code == 200
    assert js.status_code == 200


def test_websocket_receives_emitted_events() -> None:
    hub = UIHub()
    client = TestClient(create_app(hub))

    with client.websocket_connect("/ws") as websocket:
        asyncio.run(hub.emit("status", state="thinking"))
        message = json.loads(websocket.receive_text())

    assert message == {"type": "status", "payload": {"state": "thinking"}}


def test_two_websocket_clients_both_receive_events() -> None:
    hub = UIHub()
    client = TestClient(create_app(hub))

    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        asyncio.run(hub.emit("user_message", text="hallo"))
        message_a = json.loads(ws_a.receive_text())
        message_b = json.loads(ws_b.receive_text())

    assert message_a == {"type": "user_message", "payload": {"text": "hallo"}}
    assert message_b == message_a


def test_websocket_forwards_chat_input_to_shared_queue() -> None:
    hub = UIHub()
    input_queue: "asyncio.Queue[str]" = asyncio.Queue()
    client = TestClient(create_app(hub, input_queue))

    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"type": "chat", "text": "Hallo Jarvis"}))
        assert _wait_until(lambda: not input_queue.empty())

    assert input_queue.get_nowait() == "Hallo Jarvis"


def test_websocket_ignores_malformed_or_irrelevant_payloads() -> None:
    hub = UIHub()
    input_queue: "asyncio.Queue[str]" = asyncio.Queue()
    client = TestClient(create_app(hub, input_queue))

    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("kein json")
        websocket.send_text(json.dumps({"type": "other", "text": "ignoriert"}))
        websocket.send_text(json.dumps({"type": "chat", "text": "   "}))
        websocket.send_text(json.dumps({"type": "chat", "text": "echte Nachricht"}))
        assert _wait_until(lambda: not input_queue.empty())

    assert input_queue.get_nowait() == "echte Nachricht"
    assert input_queue.empty()


def test_websocket_without_input_queue_ignores_chat_messages() -> None:
    hub = UIHub()
    client = TestClient(create_app(hub))

    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"type": "chat", "text": "niemand hoert zu"}))
        asyncio.run(hub.emit("status", state="idle"))
        message = json.loads(websocket.receive_text())

    assert message == {"type": "status", "payload": {"state": "idle"}}
