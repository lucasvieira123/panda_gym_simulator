import json
import queue
import socket
import threading
import time
from typing import Optional

_PORT = 5556
_SEND_INTERVAL = 1.0


class ManagerBridge:
    """TCP server que envia percepção ao manager e recebe comandos de volta."""

    def __init__(self, port: int = _PORT) -> None:
        self._conn: Optional[socket.socket] = None
        self._conn_lock = threading.Lock()
        self._command_slot: queue.Queue = queue.Queue(maxsize=1)
        self._last_send: float = 0.0
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", port))
        self._server.listen(1)
        threading.Thread(target=self._accept_loop, daemon=True).start()
        print(f"[Bridge] Aguardando manager na porta {port}...")

    # ── API pública ────────────────────────────────────────────────────────────

    def send_perception(self, data: dict) -> None:
        """Envia percepção para o manager. Throttled a 1 envio/segundo."""
        now = time.monotonic()
        if now - self._last_send < _SEND_INTERVAL:
            return
        self._last_send = now
        self._send({"type": "perception", **data})

    def get_command(self) -> Optional[dict]:
        """Retorna o comando mais recente do manager, ou None."""
        try:
            return self._command_slot.get_nowait()
        except queue.Empty:
            return None

    @property
    def is_connected(self) -> bool:
        with self._conn_lock:
            return self._conn is not None

    # ── internos ───────────────────────────────────────────────────────────────

    def _accept_loop(self) -> None:
        while True:
            try:
                conn, addr = self._server.accept()
                print(f"[Bridge] Manager conectado ({addr[0]}:{addr[1]})")
                with self._conn_lock:
                    self._conn = conn
                threading.Thread(target=self._receive_loop, args=(conn,), daemon=True).start()
            except OSError:
                break

    def _receive_loop(self, conn: socket.socket) -> None:
        buf = ""
        with conn:
            while True:
                data = conn.recv(4096)
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
                        if msg.get("type") == "command":
                            try:
                                self._command_slot.put_nowait(msg)
                            except queue.Full:
                                self._command_slot.get_nowait()
                                self._command_slot.put_nowait(msg)
                    except json.JSONDecodeError:
                        pass
        with self._conn_lock:
            if self._conn is conn:
                self._conn = None
        print("[Bridge] Manager desconectado.")

    def _send(self, msg: dict) -> None:
        with self._conn_lock:
            if self._conn is None:
                return
            try:
                self._conn.sendall((json.dumps(msg) + "\n").encode("utf-8"))
            except OSError:
                self._conn = None