import json
import queue
import socket
import threading
import time
from typing import Optional

_HOST = "127.0.0.1"
_PORT = 5556


class ManagingBridge:
    """TCP client que recebe percepção do managing e envia comandos de volta."""

    def __init__(self, host: str = _HOST, port: int = _PORT) -> None:
        self._host = host
        self._port = port
        self._conn: Optional[socket.socket] = None
        self._perception_slot: queue.Queue = queue.Queue(maxsize=1)
        self._conn = self._connect()
        threading.Thread(target=self._receive_loop, daemon=True).start()

    # ── API pública ────────────────────────────────────────────────────────────

    def get_perception(self, timeout: float = 10.0) -> Optional[dict]:
        """Bloqueia até receber uma nova percepção (ou timeout)."""
        try:
            return self._perception_slot.get(timeout=timeout)
        except queue.Empty:
            return None

    def send_command(self, strategy: str) -> None:
        """Envia estratégia para o managing."""
        if self._conn is None:
            return
        msg = {"type": "command", "strategy": strategy}
        try:
            self._conn.sendall((json.dumps(msg) + "\n").encode("utf-8"))
        except OSError:
            self._conn = None

    # ── internos ───────────────────────────────────────────────────────────────

    def _connect(self) -> socket.socket:
        print(f"[Bridge] Conectando ao managing ({self._host}:{self._port})...", end="", flush=True)
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self._host, self._port))
                print(" OK")
                return s
            except ConnectionRefusedError:
                print(".", end="", flush=True)
                time.sleep(0.5)

    def _receive_loop(self) -> None:
        buf = ""
        while True:
            try:
                data = self._conn.recv(4096)
            except OSError:
                break
            if not data:
                break
            buf += data.decode("utf-8")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    if msg.get("type") == "perception":
                        try:
                            self._perception_slot.put_nowait(msg)
                        except queue.Full:
                            self._perception_slot.get_nowait()
                            self._perception_slot.put_nowait(msg)
                except json.JSONDecodeError:
                    pass
        print("[Bridge] Conexão com managing perdida.")