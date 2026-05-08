import os
import requests


TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def enviar_telegram(mensaje):
    try:
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            return False

        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje
        }

        r = requests.post(url, data=payload, timeout=10)

        return r.status_code == 200

    except Exception:
        return False
