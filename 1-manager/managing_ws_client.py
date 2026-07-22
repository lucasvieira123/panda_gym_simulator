import json
import queue
import threading
import time

import requests
from websockets.sync.client import connect


class ManagingWsClient:
    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        self._ws_url   = f"ws://{host}:{port}/ws/perception"
        self._http_url = f"http://{host}:{port}"
        self._queue: queue.Queue = queue.Queue(maxsize=1)
        threading.Thread(target=self._receive_loop, daemon=True).start()

    def get_perception(self, timeout: float = 10.0) -> dict | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                return self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
        return None

    def send_command(self, strategy: str) -> None:
        try:
            requests.put(
                f"{self._http_url}/task",
                json={"strategy": strategy},
                timeout=2.0,
            )
        except Exception:
            pass

    def _receive_loop(self) -> None:
        while True:
            try:
                with connect(self._ws_url, open_timeout=1.0) as ws:
                    print(f"[WsClient] Conectado a {self._ws_url}")
                    for raw in ws:
                        msg = json.loads(raw)
                        try:
                            self._queue.put_nowait(msg)
                        except queue.Full:
                            self._queue.get_nowait()
                            self._queue.put_nowait(msg)
            except Exception as e:
                print(f"[WsClient] Desconectado ({e}). Reconectando em 0.01s...")
                time.sleep(0.01)
