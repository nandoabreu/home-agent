import subprocess
from pathlib import Path
import shlex

import requests
import telebot

from telegram_reader.config import settings
from telegram_reader.opencode_client import (
    _base_url,
    ensure_opencode_server,
    is_opencode_server_active,
)

_sessions: dict[int, str] = {}
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _admin_user_ids() -> set[int]:
    raw_ids = settings.telegram_admin_user_ids.strip()
    if not raw_ids:
        return set()
    return {int(part.strip()) for part in raw_ids.split(",") if part.strip()}


def _is_admin_user(user_id: int) -> bool:
    res = user_id in _admin_user_ids()
    print(f"User {user_id} is admin: {res}")
    return res


def restart_service() -> None:
    command = shlex.split(settings.restart_command)
    subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _get_or_create_session(chat_id: int) -> str:
    if chat_id in _sessions:
        return _sessions[chat_id]

    r = requests.post(f"{_base_url()}/session", json={})
    r.raise_for_status()
    session_id = r.json()["id"]
    _sessions[chat_id] = session_id
    print(f"New session created for chat {chat_id}: {session_id}")
    return session_id


def send_to_opencode(chat_id: int, message_text: str) -> str:
    session_id = _get_or_create_session(chat_id)

    msg_url = f"{_base_url()}/session/{session_id}/message"
    r = requests.post(
        msg_url,
        json={"parts": [{"type": "text", "text": message_text}]},
    )
    if r.status_code != 200:
        print(f"Failed to send to opencode server: {r.status_code} {r.text}")
        return "Failed to send to opencode server"

    data = r.json()
    parts = data.get("parts", [])

    answer = next(
        (p["text"] for p in reversed(parts) if p.get("type") == "text" and p.get("text")),
        "No response from opencode server",
    )

    step = next((p for p in reversed(parts) if p.get("type") == "step-finish"), None)
    if step:
        print(f"Cost: {step.get('cost')}, Tokens: {step.get('tokens')}")

    print(f"Opencode answer: {answer}")
    return answer


bot = telebot.TeleBot(settings.telegram_bot_token)


@bot.message_handler(commands=["restart"])
def handle_restart(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None

    if not (user_id and _is_admin_user(user_id)):
        print(f"Ignored restart request from unauthorised user {user_id}")
        return

    bot.send_message(chat_id, "Restarting service now... Resume our chat in around 5 seconds.")
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

    bot.send_chat_action(chat_id, 'typing')
    print(f"Message from {message.from_user.id} ({message.from_user.first_name}): {user_msg}")

    if not _is_admin_user(message.from_user.id):
        msg = f"I am currently not accepting messages other from my admin user in this version. Please come again in our next version! :)"
        res = bot.send_message(chat_id, msg)
        print(msg)
        return

    response = send_to_opencode(chat_id, user_msg)
    res = bot.send_message(chat_id, response)
    print(f"Telegram Bot responded: {res.text}")


if __name__ == "__main__":
    if is_opencode_server_active():
        print("Opencode server is already running via systemd.")
    else:
        print("Opencode server is not running. Attempting to start...")
        if not ensure_opencode_server():
            raise RuntimeError("Failed to start opencode server")
        print(f"Opencode server started at {settings.opencode_server_url}")

    print("Starting Telegram bot...")
    bot.polling()
