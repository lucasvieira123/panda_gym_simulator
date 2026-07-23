import asyncio
import queue
import threading

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# ── WebSocket broadcast ───────────────────────────────────────────────────────
_ws_loop: asyncio.AbstractEventLoop | None = None
_ws_queues: set = set()   # uma asyncio.Queue por cliente WS conectado
_ready = threading.Event()  # sinaliza quando uvicorn está de fato escutando

# ── HTTP perception (desativado — usar WebSocket) ─────────────────────────────
# _perception_slot: dict = {}

_obstacles_slot:  dict = {}
_objects_slot:    dict = {}
_command_queue:     queue.Queue = queue.Queue(maxsize=1)
_waypoints_queue:   queue.Queue = queue.Queue(maxsize=1)
_environment_queue: queue.Queue = queue.Queue(maxsize=1)
_goal_queue:        queue.Queue = queue.Queue(maxsize=1)

app = FastAPI()


@app.on_event("startup")
async def _capture_event_loop():
    global _ws_loop
    _ws_loop = asyncio.get_event_loop()
    _ready.set()


# ── HTTP GET perception (desativado — usar WebSocket) ─────────────────────────
# @app.get("/perception")
# def get_perception():
#     return _perception_slot


@app.websocket("/ws/perception")
async def ws_perception(websocket: WebSocket):
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


@app.get("/environment/obstacles")
def get_obstacles():
    return _obstacles_slot


@app.get("/environment/objects")
def get_objects():
    return _objects_slot


@app.put("/task")
def put_task(body: dict):
    try:
        _command_queue.put_nowait(body)
    except queue.Full:
        _command_queue.get_nowait()
        _command_queue.put_nowait(body)
    return {"ok": True}


@app.put("/waypoints")
def put_waypoints(body: dict):
    try:
        _waypoints_queue.put_nowait(body)
    except queue.Full:
        _waypoints_queue.get_nowait()
        _waypoints_queue.put_nowait(body)
    return {"ok": True}


@app.put("/environment")
def put_environment(body: dict):
    try:
        _environment_queue.put_nowait(body)
    except queue.Full:
        _environment_queue.get_nowait()
        _environment_queue.put_nowait(body)
    return {"ok": True}


@app.put("/goal")
def put_goal(body: dict):
    try:
        _goal_queue.put_nowait(body)
    except queue.Full:
        _goal_queue.get_nowait()
        _goal_queue.put_nowait(body)
    return {"ok": True}



# ── HTTP update_perception (desativado — usar WebSocket) ──────────────────────
# def update_perception(msg: dict) -> None:
#     _perception_slot.clear()
#     _perception_slot.update(msg)

def update_perception(msg: dict) -> None:
    if not _ws_queues or _ws_loop is None:
        return
    snapshot = dict(msg)
    for q in list(_ws_queues):
        _ws_loop.call_soon_threadsafe(q.put_nowait, snapshot)


def update_obstacles(data: dict) -> None:
    _obstacles_slot.clear()
    _obstacles_slot.update(data)


def update_objects(data: dict) -> None:
    _objects_slot.clear()
    _objects_slot.update(data)


def get_command() -> dict | None:
    try:
        return _command_queue.get_nowait()
    except queue.Empty:
        return None


def get_waypoints() -> dict | None:
    try:
        return _waypoints_queue.get_nowait()
    except queue.Empty:
        return None


def get_environment_changes() -> dict | None:
    try:
        return _environment_queue.get_nowait()
    except queue.Empty:
        return None


def get_goal_changes() -> dict | None:
    try:
        return _goal_queue.get_nowait()
    except queue.Empty:
        return None


def wait_for_client(timeout: float = 60.0) -> None:
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _ws_queues:
            print("[Managing] Manager conectado. Iniciando simulação...")
            return
        time.sleep(0.05)
    print("[Managing] Nenhum manager conectado. Continuando mesmo assim...")


def start(host: str = "0.0.0.0", port: int = 8000) -> None:
    threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": host, "port": port, "log_level": "warning"},
        daemon=True,
    ).start()
    _ready.wait(timeout=10.0)  # bloqueia até uvicorn estar de fato escutando
