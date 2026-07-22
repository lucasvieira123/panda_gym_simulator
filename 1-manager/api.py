import asyncio
import threading

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# ── WebSocket broadcast ───────────────────────────────────────────────────────
_ws_loop: asyncio.AbstractEventLoop | None = None
_ws_queues: set = set()

app = FastAPI()


@app.on_event("startup")
async def _capture_event_loop():
    global _ws_loop
    _ws_loop = asyncio.get_event_loop()


@app.websocket("/ws/state")
async def ws_state(websocket: WebSocket):
    await websocket.accept()
    q: asyncio.Queue = asyncio.Queue()
    _ws_queues.add(q)
    try:
        while True:
            msg = await q.get()
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        pass
    finally:
        _ws_queues.discard(q)


def update_state(payload: dict) -> None:
    if not _ws_queues or _ws_loop is None:
        return
    snapshot = dict(payload)
    for q in list(_ws_queues):
        _ws_loop.call_soon_threadsafe(q.put_nowait, snapshot)


def start(port: int = 8001) -> None:
    threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": "0.0.0.0", "port": port, "log_level": "warning"},
        daemon=True,
    ).start()
