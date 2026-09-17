import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .hub import UIHub

STATIC_DIR = Path(__file__).parent / "static"


async def _forward_hub_events(websocket: WebSocket, queue: "asyncio.Queue[str]") -> None:
    while True:
        message = await queue.get()
        await websocket.send_text(message)


async def _forward_chat_input(
    websocket: WebSocket, input_queue: "asyncio.Queue[str] | None"
) -> None:
    while True:
        raw = await websocket.receive_text()
        if input_queue is None:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or data.get("type") != "chat":
            continue
        text = data.get("text")
        if isinstance(text, str) and text.strip():
            await input_queue.put(text.strip())


def create_app(
    hub: UIHub, input_queue: "asyncio.Queue[str] | None" = None
) -> FastAPI:
    """Baut die FastAPI-App fuer das Display-HUD.

    `input_queue` ist dieselbe Queue, aus der auch Konsole und Sprach-Pipeline
    Nutzereingaben in den Agenten speisen - die Browser-Chat-Eingabe reiht sich
    dort einfach mit ein (Producer/Consumer-Pattern), ohne dass der Agent
    zwischen den Eingabequellen unterscheiden muss.
    """
    app = FastAPI()
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        queue = hub.subscribe()
        sender = asyncio.create_task(_forward_hub_events(websocket, queue))
        receiver = asyncio.create_task(_forward_chat_input(websocket, input_queue))
        try:
            done, pending = await asyncio.wait(
                {sender, receiver}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                task.exception()
        finally:
            hub.unsubscribe(queue)

    return app
