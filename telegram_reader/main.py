import os
import glob
import subprocess
import threading
import time
import requests
import telebot

from telegram_reader.config import settings

OPENCODE_PORT = 4096
OPENCODE_HOST = "127.0.0.1"
OPENCODE_CONTEXT_DIR = os.path.expanduser("~/.opencode")
OPENCODE_CONTEXT_FILE = os.path.join(OPENCODE_CONTEXT_DIR, ".opencode_context.json")
MAX_CONTEXT_FILES = 5


def rotate_context_files():
    if not os.path.exists(OPENCODE_CONTEXT_DIR):
        os.makedirs(OPENCODE_CONTEXT_DIR, mode=0o700)
        return

    existing = sorted(
        glob.glob(os.path.join(OPENCODE_CONTEXT_DIR, ".opencode_context*.json"))
    )
    for old_file in existing[:-MAX_CONTEXT_FILES]:
        try:
            os.remove(old_file)
        except OSError:
            pass

    current = OPENCODE_CONTEXT_FILE
    if os.path.exists(current):
        idx = 1
        while os.path.exists(current):
            idx += 1
            current = os.path.join(
                OPENCODE_CONTEXT_DIR, f".opencode_context{idx}.json"
            )
        try:
            os.rename(OPENCODE_CONTEXT_FILE, current)
        except OSError:
            pass

    if os.path.exists(OPENCODE_CONTEXT_FILE):
        os.chmod(OPENCODE_CONTEXT_FILE, 0o600)


def wait_for_opencode_server(timeout: int = 30) -> bool:
    url = f"http://{OPENCODE_HOST}:{OPENCODE_PORT}/global/health"
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
    rotate_context_files()
    proc = subprocess.Popen(
        ["opencode", "serve", "--port", str(OPENCODE_PORT), "--hostname", OPENCODE_HOST],
        env={**os.environ, "OPENCODE_CONTEXT_DIR": OPENCODE_CONTEXT_DIR},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_for_opencode_server():
        proc.kill()
        raise RuntimeError("Opencode server failed to start")
    return proc


def send_to_opencode(message_text: str) -> str:
    print(f"Got: {message_text}")
    url = f"http://{OPENCODE_HOST}:{OPENCODE_PORT}/session"
    r = requests.post(url, json={})

    if r.status_code != 200:
        print(f"Can´t talk to opencode server: {r.status_code} {r.text}")
        return "Failed to create session"
    session_id = r.json()["id"]

    msg_url = f"http://{OPENCODE_HOST}:{OPENCODE_PORT}/session/{session_id}/message"
    r = requests.post(
        msg_url,
        json={"parts": [{"type": "text", "text": message_text}]},
    )
    if r.status_code != 200:
        print(f"Failed to send message: {r.status_code} {r.text}")
        return "Failed to send message"

    data = r.json()
    parts = data.get("parts", [])

    if parts:
        answer = parts[-2].get("text", "Couldn't fetch answer")
        cost = parts[-1].get("cost", "Couldn't fetch costs")
        tokens = parts[-1].get("tokens", "Couldn't fetch tokens")
        print(f"Cost: {cost}, Tokens: {tokens}")
        print(f"Answer: {answer}")
        return answer

    return "No response"


bot = telebot.TeleBot(settings.telegram_bot_token)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_msg = message.text
    chat_id = message.chat.id

    bot.send_message(chat_id, "Working on it...")
    print(f"Message from {message.from_user.first_name}: {user_msg}")

    response = send_to_opencode(user_msg)
    bot.send_message(chat_id, response)


if __name__ == "__main__":
    print("Starting opencode server...")
    opencode_proc = start_opencode_server()
    print(f"Opencode server running at http://{OPENCODE_HOST}:{OPENCODE_PORT}")

    print("Starting Telegram bot...")
    bot.polling()
