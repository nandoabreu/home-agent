import subprocess
import threading
import time
import requests
import telebot

from telegram_reader.config import settings

OPENCODE_PORT = 4096
OPENCODE_HOST = "127.0.0.1"


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
    proc = subprocess.Popen(
        ["opencode", "serve", "--port", str(OPENCODE_PORT), "--hostname", OPENCODE_HOST],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_for_opencode_server():
        proc.kill()
        raise RuntimeError("Opencode server failed to start")
    return proc


def send_to_opencode(message_text: str) -> str:
    url = f"http://{OPENCODE_HOST}:{OPENCODE_PORT}/session"
    r = requests.post(url, json={})
    if r.status_code != 200:
        return "Failed to create session"
    session_id = r.json()["id"]

    msg_url = f"http://{OPENCODE_HOST}:{OPENCODE_PORT}/session/{session_id}/message"
    r = requests.post(
        msg_url,
        json={"parts": [{"type": "text", "text": message_text}]},
    )
    if r.status_code != 200:
        return "Failed to send message"

    data = r.json()
    parts = data.get("parts", [])
    if parts:
        return parts[-1].get("text", "No response")
    return "No response"


bot = telebot.TeleBot(settings.telegram_bot_token)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_msg = message.text
    chat_id = message.chat.id

    print(f"Message from {message.from_user.first_name}: {user_msg}")

    response = send_to_opencode(user_msg)
    bot.send_message(chat_id, response)


if __name__ == "__main__":
    print("Starting opencode server...")
    opencode_proc = start_opencode_server()
    print(f"Opencode server running at http://{OPENCODE_HOST}:{OPENCODE_PORT}")

    print("Starting Telegram bot...")
    bot.polling()
