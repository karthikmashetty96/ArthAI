import requests
from src.config import settings
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class NotificationResult:
    ok: bool
    message: str


def send_telegram_alert(message: str) -> NotificationResult:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        msg = "Telegram credentials missing in .env. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID."
        logger.warning(msg)
        return NotificationResult(False, msg)

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": settings.telegram_chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        res = requests.post(url, json=payload, timeout=10)
        try:
            data = res.json()
        except ValueError:
            data = {}

        if res.status_code == 200 and data.get("ok", True):
            return NotificationResult(True, "Sent to Telegram")

        detail = data.get("description") or res.text or f"HTTP {res.status_code}"
        msg = f"Telegram not sent: {detail}"
        logger.error(msg)
        return NotificationResult(False, msg)
    except Exception as e:
        msg = f"Telegram network error: {e}"
        logger.error(msg)
        return NotificationResult(False, msg)


def broadcast_telegram_alert(message: str) -> bool:
    return send_telegram_alert(message).ok
