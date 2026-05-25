import logging
import threading
from datetime import datetime
from typing import Any

from src.config import settings

logger = logging.getLogger(__name__)

try:
    from SmartApi.smartWebSocketV2 import SmartWebSocketV2
except Exception:  # pragma: no cover - optional broker SDK
    SmartWebSocketV2 = None


EXCHANGE_TYPE = {
    "NSE": 1,
    "BSE": 3,
}

MODE_LTP = 1


class AngelStreamStore:
    """Small process-local store for Angel One websocket ticks with LRU memory limit."""

    def __init__(self, max_ticks: int = 500):
        self._lock = threading.Lock()
        self._ticks: dict[str, dict[str, Any]] = {}
        self._max_ticks = max_ticks
        self._access_order: list[str] = []  # For LRU eviction
        self._thread: threading.Thread | None = None
        self._socket = None
        self._subscription_key = ""
        self._last_attempt = 0.0
        self.status = "idle"
        self.last_error = ""

    def latest(self, token: str | int | None) -> dict | None:
        if not token:
            return None
        with self._lock:
            return self._ticks.get(str(token))
    
    def _evict_lru(self):
        """Remove least recently used tick if cache exceeds max size."""
        if len(self._ticks) >= self._max_ticks and self._access_order:
            lru_token = self._access_order.pop(0)
            if lru_token in self._ticks:
                del self._ticks[lru_token]
                logger.debug(f"Evicted LRU tick for token {lru_token}")

    def available(self) -> bool:
        return SmartWebSocketV2 is not None

    def start(
        self,
        jwt_token: str | None,
        feed_token: str | None,
        watchlist: list[dict],
    ) -> tuple[bool, str]:
        if not self.available():
            return False, "Install smartapi-python to enable Angel WebSocket ticks."
        if not jwt_token or not feed_token:
            return False, "Angel feed token missing. Reconnect Angel One."

        now = datetime.now().timestamp()
        with self._lock:
            if self.status == "error" and now - self._last_attempt < 30:
                return False, f"Stream cooling down after error: {self.last_error or 'connection failed'}"

        token_groups = self._token_groups(watchlist)
        if not token_groups:
            return False, "No streamable tokens selected."

        subscription_key = repr(token_groups)
        with self._lock:
            if self._thread and self._thread.is_alive() and self._subscription_key == subscription_key:
                return True, self.status

            self._subscription_key = subscription_key
            self._last_attempt = now
            self.status = "connecting"
            self.last_error = ""
        
        self._thread = threading.Thread(
            target=self._run,
            args=(jwt_token, feed_token, token_groups),
            daemon=True,
        )
        self._thread.start()
        return True, "connecting"

    def _token_groups(self, watchlist: list[dict]) -> list[dict]:
        grouped: dict[int, list[str]] = {}
        for stock in watchlist:
            token = stock.get("token")
            exchange_type = EXCHANGE_TYPE.get(str(stock.get("exchange", "")).upper())
            if not token or not exchange_type:
                continue
            grouped.setdefault(exchange_type, []).append(str(token))
        return [
            {"exchangeType": exchange_type, "tokens": sorted(set(tokens))}
            for exchange_type, tokens in grouped.items()
        ]

    def _run(self, jwt_token: str, feed_token: str, token_groups: list[dict]):
        try:
            socket = SmartWebSocketV2(
                jwt_token,
                settings.angel_api_key,
                settings.angel_client_code,
                feed_token,
            )
            self._socket = socket

            def on_open(wsapp):
                self.status = "streaming"
                socket.subscribe("arthai_watchlist", MODE_LTP, token_groups)

            def on_data(wsapp, message):
                token = str(message.get("token") or message.get("symbol_token") or "")
                if not token:
                    return
                tick = dict(message)
                tick["timestamp"] = datetime.now().strftime("%H:%M:%S")
                tick["price"] = self._normalise_price(
                    tick.get("last_traded_price")
                    or tick.get("ltp")
                    or tick.get("last_traded_price_in_paise")
                )
                with self._lock:
                    self._ticks[token] = tick
                    # Update LRU order
                    if token in self._access_order:
                        self._access_order.remove(token)
                    self._access_order.append(token)
                    # Evict if needed
                    self._evict_lru()

            def on_error(wsapp, error):
                with self._lock:
                    self.status = "error"
                    self.last_error = str(error)
                logger.warning("Angel stream error: %s", error)

            def on_close(wsapp, *args):
                with self._lock:
                    if self.status != "error":
                        self.status = "closed"

            socket.on_open = on_open
            socket.on_data = on_data
            socket.on_error = on_error
            socket.on_close = on_close
            socket.connect()
        except Exception as exc:
            self.status = "error"
            self.last_error = str(exc)
            logger.exception("Angel stream failed")

    @staticmethod
    def _normalise_price(value):
        if value is None:
            return None
        try:
            price = float(value)
        except (TypeError, ValueError):
            return None
        return price / 100 if abs(price) > 100000 else price


stream_store = AngelStreamStore()
