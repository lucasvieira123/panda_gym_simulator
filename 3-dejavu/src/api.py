import asyncio
import threading

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# ── WebSocket broadcast (DejaVu Console) ─────────────────────────────────────
_ws_loop: asyncio.AbstractEventLoop | None = None
_ws_queues: set = set()
_console_ready = threading.Event()

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
    _console_ready.set()
    try:
        while True:
            msg = await q.get()
            try:
                await websocket.send_json(msg)
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _ws_queues.discard(q)


def update_state(payload: dict) -> None:
    if not _ws_queues or _ws_loop is None:
        return
    snapshot = dict(payload)
    for q in list(_ws_queues):
        _ws_loop.call_soon_threadsafe(q.put_nowait, snapshot)


def wait_for_console(timeout: float = 120.0) -> None:
    """Bloqueia até o DejaVu Console conectar via WS."""
    if _console_ready.wait(timeout=timeout):
        print("[DejaVu] Console conectado.")
    else:
        print("[DejaVu] Console nao conectou. Continuando mesmo assim...")


def start(port: int = 8002) -> None:
    threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": "0.0.0.0", "port": port, "log_level": "warning"},
        daemon=True,
    ).start()
