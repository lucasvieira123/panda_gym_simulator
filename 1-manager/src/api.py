import asyncio
import threading

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from ts import ts

# ── WebSocket broadcast ───────────────────────────────────────────────────────
_ws_loop: asyncio.AbstractEventLoop | None = None
_ws_queues: set = set()
_dashboard_ready = threading.Event()  # sinaliza quando o primeiro cliente WS (GUI) conectou

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
    _dashboard_ready.set()          # GUI conectou — libera wait_for_dashboard()
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


def wait_for_dashboard(timeout: float = 120.0) -> None:
    """Bloqueia até o GUI conectar via WS — espelho de wait_for_client() no managing."""
    if _dashboard_ready.wait(timeout=timeout):
        print(f"[{ts()}][Manager] GUI conectado.")
    else:
        print(f"[{ts()}][Manager] GUI nao conectou. Continuando mesmo assim...")


def start(port: int = 8001) -> None:
    threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": "0.0.0.0", "port": port, "log_level": "warning"},
        daemon=True,
    ).start()
