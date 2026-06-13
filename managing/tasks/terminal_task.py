import ast
import os
import queue
import socket
import subprocess
import sys
import threading
from typing import Callable, List

import numpy as np

from ._object_task import _ObjectTask

_PORT = 5555
_CLIENT_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input_client.py")


class TerminalTask(_ObjectTask):
    """Executa waypoints recebidos via terminal separado.

    Ao iniciar, abre uma janela nova onde o usuário digita os comandos.

    Aceita um waypoint:   [x, y, z, gripper]
    Aceita sequência:     [[x, y, z, g], [x, y, z, g], ...]

    gripper: 1.0 = aberta, -1.0 = fechada.
    """

    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        target_goal_cfg: dict,
        object_cfg: dict,
        task_cfg: dict = None,
    ) -> None:
        super().__init__(sim, get_ee_position, get_object_position, target_goal_cfg, object_cfg, task_cfg)
        _task = task_cfg or {}
        self.step_threshold = _task.get("phase_threshold", 0.02)
        self._waypoints: List[np.ndarray] = []
        self._current = 0
        self._queue: queue.Queue = queue.Queue()
        self._start_server()
        self._open_input_terminal()

    # ── socket server ─────────────────────────────────────────────────────────

    def _start_server(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", _PORT))
        self._server.listen(5)
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self) -> None:
        while True:
            try:
                conn, _ = self._server.accept()
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except OSError:
                break

    def _handle_client(self, conn: socket.socket) -> None:
        buf = ""
        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                buf += data.decode("utf-8")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parsed = ast.literal_eval(line)
                        if isinstance(parsed[0], (int, float)):
                            parsed = [parsed]
                        self._queue.put(parsed)
                    except (ValueError, SyntaxError) as e:
                        print(f"[Terminal] Formato inválido: {e}")

    def _open_input_terminal(self) -> None:
        subprocess.Popen(
            [sys.executable, _CLIENT_SCRIPT, str(_PORT)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

    # ── task interface ─────────────────────────────────────────────────────────

    def reset(self) -> None:
        self._waypoints = []
        self._current = 0
        super().reset()

    def compute_action(self) -> np.ndarray:
        if self._current >= len(self._waypoints):
            try:
                raw = self._queue.get_nowait()
                self._waypoints = [np.array(w, dtype=np.float32) for w in raw]
                self._current = 0
                print(f"[Terminal] {len(self._waypoints)} waypoint(s) recebido(s)")
            except queue.Empty:
                return np.zeros(4, dtype=np.float32)

        ee_pos     = np.array(self.get_ee_position())
        target     = self._waypoints[self._current]
        target_pos = target[:3]
        gripper    = target[3]
        direction  = target_pos - ee_pos
        dist       = np.linalg.norm(direction)

        if dist < self.step_threshold:
            print(f"[Terminal] Waypoint {self._current + 1}/{len(self._waypoints)} concluído")
            self._current += 1
            if self._current >= len(self._waypoints):
                print("[Terminal] Sequência concluída. Aguardando próximo comando...")
                return np.zeros(4, dtype=np.float32)
            target     = self._waypoints[self._current]
            target_pos = target[:3]
            gripper    = target[3]
            direction  = target_pos - ee_pos
            dist       = np.linalg.norm(direction)

        if dist > 0:
            direction = direction / dist

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)
