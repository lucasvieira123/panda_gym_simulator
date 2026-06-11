from __future__ import annotations

import sys

import numpy as np

from .base import Behavior


_KEY_MAP = {
    "w": (1,  1.0),
    "s": (1, -1.0),
    "d": (0,  1.0),
    "a": (0, -1.0),
    "r": (2,  1.0),
    "f": (2, -1.0),
}

_CONTROLS_MSG = (
    "\n[Manual] Controles do braço:"
    "\n  W/S → frente/trás   A/D → esquerda/direita   R/F → sobe/desce"
    "\n  E → abre garra      C → fecha garra           Space → parado"
    "\n  Pressione uma tecla para avançar um step...\n"
)


class ManualBehavior(Behavior):
    """Controle manual via teclado no terminal. Cada tecla avança um step."""

    def act(self, env, observation):
        print(_CONTROLS_MSG, end="", flush=True)

        if sys.platform == "win32":
            import msvcrt
            raw = msvcrt.getch()
            try:
                key = raw.decode("utf-8").lower()
            except UnicodeDecodeError:
                key = ""
        else:
            import tty, termios
            fd  = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                key = sys.stdin.read(1).lower()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

        print(f"[Manual] tecla: {repr(key)}")

        action = np.zeros(env.action_space.shape, dtype=np.float32)
        flat   = action.reshape(-1)

        if key in _KEY_MAP:
            idx, val = _KEY_MAP[key]
            if flat.size > idx:
                flat[idx] = val
        elif key == "e" and flat.size >= 4:
            flat[3] = 1.0
        elif key == "c" and flat.size >= 4:
            flat[3] = -1.0

        try:
            flat[:] = np.clip(flat, env.action_space.low.reshape(-1), env.action_space.high.reshape(-1))
        except Exception:
            flat[:] = np.clip(flat, -1.0, 1.0)

        return action
