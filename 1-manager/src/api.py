import asyncio
import json
import queue
import threading

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from ts import ts

# ── WebSocket broadcast (dashboard) ──────────────────────────────────────────
_ws_loop: asyncio.AbstractEventLoop | None = None
_ws_queues: set = set()
_dashboard_ready = threading.Event()

# ── DejaVu checkpoint ─────────────────────────────────────────────────────────
_dj_send_queue: asyncio.Queue | None = None
_dj_response: queue.Queue = queue.Queue(maxsize=1)
_dj_connected = threading.Event()

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


@app.websocket("/ws/new_perception")
async def ws_new_perception(websocket: WebSocket):
    global _dj_send_queue
    await websocket.accept()
    _dj_send_queue = asyncio.Queue()
    _dj_connected.set()
    print(f"[{ts()}][Manager] DejaVu conectado.")
    try:
        while True:
            payload = await _dj_send_queue.get()
            await websocket.send_json(payload)
            raw = await websocket.receive_text()
            result = json.loads(raw)
            try:
                _dj_response.put_nowait(result)
            except queue.Full:
                _dj_response.get_nowait()
                _dj_response.put_nowait(result)
    except WebSocketDisconnect:
        pass
    finally:
        _dj_send_queue = None
        _dj_connected.clear()
        print(f"[{ts()}][Manager] DejaVu desconectado.")


def send_to_dejavu(payload: dict) -> dict:
    """Envia new_perception ao DejaVu e bloqueia até receber resposta.
    Retorna ok se DejaVu não estiver conectado (degrada graciosamente)."""
    if _dj_send_queue is None or _ws_loop is None:
        return {"status": "ok"}
    _ws_loop.call_soon_threadsafe(_dj_send_queue.put_nowait, payload)
    while True:
        try:
            return _dj_response.get(timeout=1.0)
        except queue.Empty:
            if not _dj_connected.is_set():
                return {"status": "ok"}


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
