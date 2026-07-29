import asyncio
import json

from fastapi.testclient import TestClient

from jarvis.ui.hub import UIHub
from jarvis.ui.server import create_app


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
