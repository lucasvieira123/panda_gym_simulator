import json
import queue
import threading
import time

import requests
from websockets.sync.client import connect
from ts import ts


class ManagingWsClient:
    _MAX_RETRIES = 3

    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        self._ws_url   = f"ws://{host}:{port}/ws/perception"
        self._http_url = f"http://{host}:{port}"
        self._queue: queue.Queue = queue.Queue(maxsize=1)
        self._alive    = True
        threading.Thread(target=self._receive_loop, daemon=True).start()

    @property
    def alive(self) -> bool:
        return self._alive

    def get_perception(self, timeout: float = 10.0) -> dict | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                return self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
        return None

    def send_command(self, payload: dict) -> None:
        try:
            requests.put(
                f"{self._http_url}/task",
                json=payload,
                timeout=2.0,
            )
        except Exception:
            pass

    def _receive_loop(self) -> None:
        retries = 0
        while retries < self._MAX_RETRIES:
            try:
                with connect(self._ws_url, open_timeout=1.0) as ws:
                    retries = 0
                    print(f"[{ts()}][WsClient] Conectado a {self._ws_url}")
                    for raw in ws:
                        msg = json.loads(raw)
                        try:
                            self._queue.put_nowait(msg)
                        except queue.Full:
                            self._queue.get_nowait()
                            self._queue.put_nowait(msg)
            except Exception as e:
                retries += 1
                print(f"[{ts()}][WsClient] Falha ({e}). Tentativa {retries}/{self._MAX_RETRIES}...")
                time.sleep(0.5)

        print(f"[{ts()}][WsClient] Sem conexão após {self._MAX_RETRIES} tentativas. Encerrando.")
        self._alive = False
