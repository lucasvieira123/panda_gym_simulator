import socket
import sys
import time


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555

    print("=" * 52)
    print("  Waypoint Input — Simulador de Braco Robotico")
    print("=" * 52)
    print("  gripper: 1.0 = aberta  |  -1.0 = fechada")
    print()
    print("  Exemplos:")
    print("    Unico  : [0.03, 0.0, 0.12, 1.0]")
    print("    Sequencia: [[0.03, 0.0, 0.12, 1.0], [0.0, 0.1, 0.2, -1.0]]")
    print("=" * 52)
    print()

    sock = _connect(port)
    if sock is None:
        input("Não foi possível conectar. Pressione Enter para fechar.")
        return

    with sock:
        while True:
            try:
                raw = input("[Waypoint]: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not raw:
                continue
            try:
                sock.sendall((raw + "\n").encode("utf-8"))
            except OSError:
                print("[Cliente] Conexão perdida.")
                break


def _connect(port: int, retries: int = 10, delay: float = 0.5) -> socket.socket | None:
    print(f"Conectando ao simulador (porta {port})...", end="", flush=True)
    for _ in range(retries):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", port))
            print(" OK\n")
            return s
        except ConnectionRefusedError:
            print(".", end="", flush=True)
            time.sleep(delay)
    print(" falhou.\n")
    return None


if __name__ == "__main__":
    main()
