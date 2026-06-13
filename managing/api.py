import queue
import threading

import uvicorn
from fastapi import FastAPI

_perception_slot: dict = {}
_command_queue: queue.Queue = queue.Queue(maxsize=1)
_waypoints_queue: queue.Queue = queue.Queue(maxsize=1)

app = FastAPI()


@app.get("/perception")
def get_perception():
    return _perception_slot


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


def update_perception(msg: dict) -> None:
    _perception_slot.clear()
    _perception_slot.update(msg)


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


def start(host: str = "0.0.0.0", port: int = 8000) -> None:
    threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": host, "port": port, "log_level": "warning"},
        daemon=True,
    ).start()
