import socket
import threading
import time
import webbrowser

import uvicorn

MAX_PORT_ATTEMPTS = 20


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def _is_nova(url: str) -> bool:
    try:
        import urllib.request

        with urllib.request.urlopen(f"{url}/api/status", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _resolve_port(host: str, port: int) -> tuple[int, bool]:
    if not _port_in_use(host, port):
        return port, False
    url = f"http://{host}:{port}"
    if _is_nova(url):
        print(f"[NOVA] Ja existe uma NOVA rodando em {url} - abrindo interface existente.")
        return port, True
    for delta in range(1, MAX_PORT_ATTEMPTS + 1):
        candidate = port + delta
        if not _port_in_use(host, candidate):
            print(f"[NOVA] Porta {port} ocupada por outro programa - usando porta {candidate}.")
            return candidate, False
    raise RuntimeError(f"nenhuma porta livre encontrada entre {port} e {port + MAX_PORT_ATTEMPTS}")


def _wait_server(url: str, timeout_s: float = 25.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _is_nova(url):
            return
        time.sleep(0.3)


def _start_server(settings, port: int) -> None:
    from backend.app.main import get_app

    threading.Thread(
        target=lambda: uvicorn.run(
            get_app(),
            host=settings.host,
            port=port,
            log_level="warning",
        ),
        daemon=True,
    ).start()


def run_desktop() -> None:
    from backend.app.config import get_settings

    settings = get_settings()
    port, reuse = _resolve_port(settings.host, settings.port)
    url = f"http://{settings.host}:{port}"

    if not reuse:
        _start_server(settings, port)
        _wait_server(url)

    try:
        import webview

        webview.create_window(
            "NOVA",
            url,
            width=1280,
            height=820,
            min_size=(980, 640),
            background_color="#0b0f14",
        )
        webview.start()
    except Exception as exc:
        print(f"[NOVA] Janela nativa indisponivel ({exc}); abrindo navegador padrao.")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


def run_server_only() -> None:
    from backend.app.config import get_settings
    from backend.app.main import get_app

    settings = get_settings()
    port, reuse = _resolve_port(settings.host, settings.port)
    url = f"http://{settings.host}:{port}"

    if reuse:
        print(f"[NOVA] Servidor ja ativo em {url}. Nada a fazer (Ctrl+C para sair).")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    uvicorn.run(get_app(), host=settings.host, port=port, log_level="info")


if __name__ == "__main__":
    import sys

    if "--server-only" in sys.argv:
        run_server_only()
    else:
        run_desktop()
