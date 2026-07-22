import time
import requests


class ManagingClient:
    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        self._base = f"http://{host}:{port}"

    def get_perception(self, timeout: float = 10.0) -> dict | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                r = requests.get(f"{self._base}/perception", timeout=2.0)
                data = r.json()
                if data:
                    return data
            except Exception:
                pass
            time.sleep(0.5)
        return None

    def send_command(self, strategy: str) -> None:
        try:
            requests.put(
                f"{self._base}/task",
                json={"strategy": strategy},
                timeout=2.0,
            )
        except Exception:
            pass
