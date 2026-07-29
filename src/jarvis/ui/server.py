from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .hub import UIHub

STATIC_DIR = Path(__file__).parent / "static"


def create_app(hub: UIHub) -> FastAPI:
    app = FastAPI()
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        queue = hub.subscribe()
        try:
            while True:
                message = await queue.get()
                await websocket.send_text(message)
        except WebSocketDisconnect:
            pass
        finally:
            hub.unsubscribe(queue)

    return app
