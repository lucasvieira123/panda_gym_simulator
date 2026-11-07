"""Grava a janela do PyBullet em MP4, tal como aparece na tela (cena, câmera e HUD).

Usa o registro nativo do PyBullet (STATE_LOGGING_VIDEO_MP4), que envia os quadros da janela a
um executável chamado `ffmpeg`, procurado pelo nome no PATH. O ffmpeg vem do pacote
`imageio-ffmpeg` (ou do sistema, se houver) e é exposto com esse nome só para este processo.

No Windows, o PyBullet abre esse pipe em modo texto: cada byte 0x0A da imagem vira 0x0D 0x0A e
os quadros se desalinham (cores trocadas e imagem deslocada). Por isso, no Windows, o `ffmpeg`
do PATH é um intermediário que desfaz essa conversão, que é exatamente reversível, antes de
passar os quadros ao ffmpeg real.

O PyBullet marca o vídeo como 60 fps, mas a janela é capturada mais devagar (cerca de 20 fps
com a codificação). Ao encerrar, as marcas de tempo são reescaladas, sem recodificar, para que
o vídeo dure o mesmo que a janela ficou aberta: toca na velocidade da tela, incluindo as pausas
em que a simulação espera o Manager. Só funciona com `render_mode: "human"`.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pybullet as p

from .ts import ts

_FOLDER = Path(tempfile.gettempdir()) / "dejavu_ffmpeg"

# Inverso da conversão de modo texto do Windows: cada b"\r\n" do fluxo veio de um b"\n" original
_UNDO_TEXT_MODE = '''import sys
src, dst, carry = sys.stdin.buffer, sys.stdout.buffer, b""
while True:
    chunk = src.read(1 << 20)
    if not chunk:
        break
    data = carry + chunk
    data, carry = (data[:-1], b"\\r") if data.endswith(b"\\r") else (data, b"")
    dst.write(data.replace(b"\\r\\n", b"\\n"))
dst.write(carry)
dst.flush()
'''


def _real_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found and Path(found).parent != _FOLDER:
        return found
    try:
        import imageio_ffmpeg
    except ImportError:
        return None
    return imageio_ffmpeg.get_ffmpeg_exe()


def _expose_ffmpeg(real: str) -> None:
    """Põe no PATH deste processo um `ffmpeg` que o PyBullet consegue usar."""
    _FOLDER.mkdir(exist_ok=True)
    if os.name == "nt":
        (_FOLDER / "ffmpeg.exe").unlink(missing_ok=True)  # teria prioridade sobre o .bat no PATH
        decoder = _FOLDER / "undo_text_mode.py"
        decoder.write_text(_UNDO_TEXT_MODE, encoding="utf-8")
        (_FOLDER / "ffmpeg.bat").write_text(
            f'@"{sys.executable}" "{decoder}" | "{real}" %*\r\n', encoding="utf-8")
    else:
        target = _FOLDER / "ffmpeg"
        if not target.exists():
            target.symlink_to(real)
    os.environ["PATH"] = f"{_FOLDER}{os.pathsep}{os.environ.get('PATH', '')}"


class VideoRecorder:
    """Inicia a gravação ao ser criado e a encerra em `stop()`, que pode ser chamado mais de uma vez."""

    def __init__(self, physics_client, path: str, enabled: bool, render_mode: str) -> None:
        self._client = physics_client
        self._log_id = None
        self.path    = None
        if not enabled:
            return
        if render_mode != "human":
            print(f"[{ts()}][Video] Gravação desligada: exige render_mode 'human'.")
            return
        if " " in path:
            # O PyBullet passa o caminho ao ffmpeg sem aspas
            print(f"[{ts()}][Video] Gravação desligada: o caminho tem espaços ({path}).")
            return
        self._ffmpeg = _real_ffmpeg()
        if not self._ffmpeg:
            print(f"[{ts()}][Video] Gravação desligada: ffmpeg não encontrado (pip install imageio-ffmpeg).")
            return
        _expose_ffmpeg(self._ffmpeg)
        self._log_id  = physics_client.startStateLogging(p.STATE_LOGGING_VIDEO_MP4, path)
        self._started = time.monotonic()
        self.path     = path
        print(f"[{ts()}][Video] Gravando a janela em {path}")

    def stop(self) -> None:
        if self._log_id is None:
            return
        self._client.stopStateLogging(self._log_id)
        self._log_id = None
        wall = time.monotonic() - self._started
        try:
            _retime(self._ffmpeg, self.path, wall)
            print(f"[{ts()}][Video] Gravação encerrada: {self.path} ({wall:.0f} s)")
        except Exception as error:  # o vídeo continua válido, só mais rápido que a tela
            print(f"[{ts()}][Video] Gravação encerrada sem ajuste de velocidade ({error}): {self.path}")


def _duration(ffmpeg: str, path: str) -> float:
    info = subprocess.run([ffmpeg, "-i", path], capture_output=True, text=True).stderr
    hours, minutes, seconds = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info).groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _retime(ffmpeg: str, path: str, wall_seconds: float) -> None:
    """Reescala as marcas de tempo para o vídeo durar `wall_seconds`, sem recodificar."""
    factor = wall_seconds / _duration(ffmpeg, path)
    retimed = path[:-4] + "_retimed.mp4"
    subprocess.run([ffmpeg, "-y", "-v", "error", "-itsscale", f"{factor:.6f}", "-i", path, "-c", "copy", retimed],
                   check=True, capture_output=True)
    os.replace(retimed, path)
