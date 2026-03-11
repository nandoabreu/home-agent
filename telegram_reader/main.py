import subprocess
import time
import requests
import telebot

from telegram_reader.config import settings

# In-memory mapping of Telegram chat_id -> OpenCode session_id.
# Each chat gets its own persistent session so the model retains conversation history.
_sessions: dict[int, str] = {}


def _base_url() -> str:
    return settings.opencode_server_url.rstrip("/")


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

    proc = subprocess.Popen(
        ["opencode", "serve", "--port", str(port), "--hostname", host],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_for_opencode_server():
        proc.kill()
        raise RuntimeError("Opencode server failed to start")
    return proc


def _get_or_create_session(chat_id: int) -> str:
    """Return the existing OpenCode session for this chat, or create a new one."""
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

    # Find the last text part as the assistant answer
    answer = next(
        (p["text"] for p in reversed(parts) if p.get("type") == "text" and p.get("text")),
        "No response",
    )

    # Log usage metadata from the last step part if available
    step = next((p for p in reversed(parts) if p.get("type") == "step-finish"), None)
    if step:
        print(f"Cost: {step.get('cost')}, Tokens: {step.get('tokens')}")

    print(f"Answer: {answer}")
    return answer


bot = telebot.TeleBot(settings.telegram_bot_token)


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
