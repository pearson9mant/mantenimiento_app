import os
import requests


TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TELEGRAM_CHAT_ID_GENERAL = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_CHAT_ID_JUAN = os.getenv("TELEGRAM_CHAT_ID_JUAN")
TELEGRAM_CHAT_ID_LUIS = os.getenv("TELEGRAM_CHAT_ID_LUIS")


def obtener_chat_id(centro):

    centro = str(centro or "").strip().lower()

    if centro in ["pearson 22", "p22", "pearson22"]:
        return TELEGRAM_CHAT_ID_JUAN or TELEGRAM_CHAT_ID_GENERAL

    if centro in ["pearson 9", "p9", "pearson9"]:
        return TELEGRAM_CHAT_ID_LUIS or TELEGRAM_CHAT_ID_GENERAL

    return TELEGRAM_CHAT_ID_GENERAL


def enviar_telegram(mensaje, centro=None):

    try:

        chat_id = obtener_chat_id(centro)

        if not TELEGRAM_TOKEN or not chat_id:
            return False

        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

        chat_ids = [chat_id]

        # Copia general para Juan
        if TELEGRAM_CHAT_ID_GENERAL:
            if TELEGRAM_CHAT_ID_GENERAL not in chat_ids:
                chat_ids.append(TELEGRAM_CHAT_ID_GENERAL)

        ok = True

        for chat in chat_ids:

            payload = {
                "chat_id": chat,
                "text": mensaje
            }

            r = requests.post(url, data=payload, timeout=10)

            if r.status_code != 200:
                ok = False

        return ok

    except Exception as e:
        print("ERROR TELEGRAM:", e)
        return False
