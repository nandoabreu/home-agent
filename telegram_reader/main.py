import subprocess
import time
from pathlib import Path
import shlex

import requests
import telebot

from telegram_reader.config import settings

_sessions: dict[int, str] = {}
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _base_url() -> str:
    return settings.opencode_server_url.rstrip("/")


def _admin_user_ids() -> set[int]:
    raw_ids = settings.telegram_admin_user_ids.strip()
    if not raw_ids:
        return set()
    return {int(part.strip()) for part in raw_ids.split(",") if part.strip()}


def _is_admin_user(user_id: int | None) -> bool:
    return user_id is not None and user_id in _admin_user_ids()


def restart_service() -> None:
    command = shlex.split(settings.restart_command)
    subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


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


def start_opencode_server():
    from urllib.parse import urlparse

    parsed = urlparse(settings.opencode_server_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 4096

    log_file_path = PROJECT_ROOT / "opencode_server.log"
    pointer = open(Path(log_file_path), "wb") if settings.debug_mode else subprocess.DEVNULL

    proc = subprocess.Popen(
        ["opencode", "serve", "--port", str(port), "--hostname", host],
        stdout=pointer,
        stderr=subprocess.STDOUT,
        cwd=PROJECT_ROOT,
    )
    
    if not wait_for_opencode_server():
        proc.kill()
        raise RuntimeError("Opencode server failed to start")
    return proc


def _get_or_create_session(chat_id: int) -> str:
    if chat_id in _sessions:
        return _sessions[chat_id]

    r = requests.post(f"{_base_url()}/session", json={})
    r.raise_for_status()
    session_id = r.json()["id"]
    _sessions[chat_id] = session_id
    print(f"New session {session_id} created for chat {chat_id}")
    return session_id


def send_to_opencode(chat_id: int, message_text: str) -> str:
    print(f"[chat={chat_id}] Got: {message_text}")

    session_id = _get_or_create_session(chat_id)

    msg_url = f"{_base_url()}/session/{session_id}/message"
    r = requests.post(
        msg_url,
        json={"parts": [{"type": "text", "text": message_text}]},
    )
    if r.status_code != 200:
        print(f"Failed to send message: {r.status_code} {r.text}")
        return "Failed to send message"

    data = r.json()
    parts = data.get("parts", [])

    answer = next(
        (p["text"] for p in reversed(parts) if p.get("type") == "text" and p.get("text")),
        "No response",
    )

    step = next((p for p in reversed(parts) if p.get("type") == "step-finish"), None)
    if step:
        print(f"Cost: {step.get('cost')}, Tokens: {step.get('tokens')}")

    print(f"Answer: {answer}")
    return answer


bot = telebot.TeleBot(settings.telegram_bot_token)


@bot.message_handler(commands=["restart"])
def handle_restart(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None

    if not _is_admin_user(user_id):
        print(f"Ignored restart request from unauthorised user {user_id}")
        return

    bot.send_message(chat_id, "Restarting service now...")
    restart_service()


@bot.message_handler(commands=["whoami"])
def handle_whoami(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    bot.send_message(chat_id, f"Your Telegram user id is: {user_id}")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_msg = message.text

    bot.send_message(chat_id, "Working on it...")
    print(f"Message from {message.from_user.first_name}: {user_msg}")

    response = send_to_opencode(chat_id, user_msg)
    bot.send_message(chat_id, response)


if __name__ == "__main__":
    print("Starting opencode server...")
    opencode_proc = start_opencode_server()
    print(f"Opencode server running at {settings.opencode_server_url}")

    print("Starting Telegram bot...")
    bot.polling()
