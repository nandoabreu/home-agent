import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from telegram_reader.config import settings


def _base_url() -> str:
    return settings.opencode_server_url.rstrip("/")


def is_opencode_server_active() -> bool:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "opencode-server"],
        capture_output=True,
        text=True,
    )

    print(f"Checking opencode server status: {result.stdout.strip()}")
    return result.returncode == 0


def wait_for_opencode_server(timeout: int = 30) -> bool:
    url = f"{_base_url()}/global/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    return False


def ensure_opencode_server() -> bool:
    if is_opencode_server_active():
        return True

    parsed = urlparse(settings.opencode_server_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 4096

    log_file_path = Path(__file__).resolve().parent.parent / "opencode_server.log"
    pointer = open(log_file_path, "wb") if settings.debug_mode else subprocess.DEVNULL

    proc = subprocess.Popen(
        ["opencode", "serve", "--port", str(port), "--hostname", host],
        stdout=pointer,
        stderr=subprocess.STDOUT,
        cwd=Path(__file__).resolve().parent.parent,
    )

    if not wait_for_opencode_server():
        proc.kill()
        return False
    return True
