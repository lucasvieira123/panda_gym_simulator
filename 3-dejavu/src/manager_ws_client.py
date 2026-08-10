import json
import queue
import threading
import time

from websockets.sync.client import connect


class ManagerWsClient:
    _MAX_RETRIES = None  # None = retry indefinitely

    def __init__(self, host: str = "localhost", port: int = 8001) -> None:
        self._ws_url = f"ws://{host}:{port}/ws/new_perception"
        self._queue: queue.Queue = queue.Queue(maxsize=1)
        self._alive = True
        self._ws = None
        self._lock = threading.Lock()
        threading.Thread(target=self._receive_loop, daemon=True).start()

    @property
    def alive(self) -> bool:
        return self._alive

    def get_new_perception(self, timeout: float = 10.0) -> dict | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                return self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
        return None

    def send_result(self, result: dict) -> None:
        with self._lock:
            if self._ws is not None:
                try:
                    self._ws.send(json.dumps(result))
                except Exception:
                    pass

    def _receive_loop(self) -> None:
        attempt = 0
        while True:
            try:
                with connect(self._ws_url, open_timeout=2.0) as ws:
                    with self._lock:
                        self._ws = ws
                    attempt = 0
                    print(f"[ManagerWsClient] Conectado a {self._ws_url}")
                    for raw in ws:
                        msg = json.loads(raw)
                        try:
                            self._queue.put_nowait(msg)
                        except queue.Full:
                            self._queue.get_nowait()
                            self._queue.put_nowait(msg)
            except Exception as e:
                attempt += 1
                with self._lock:
                    self._ws = None
                delay = min(0.5 * attempt, 5.0)  # backoff até 5s
                print(f"[ManagerWsClient] Falha ({e}). Tentativa {attempt}, próxima em {delay:.1f}s...")
                time.sleep(delay)
