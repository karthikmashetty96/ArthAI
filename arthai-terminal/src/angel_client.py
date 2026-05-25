# src/angel_client.py
import requests
import pyotp
import logging
import time
from datetime import datetime, timedelta
from src.config import settings
from src.utils import RateLimiter

logger = logging.getLogger(__name__)

# Hardcoded instrument tokens for major stocks (fallback)
# Note: Tokens may change; for production, fetch from master contract list
ANGEL_TOKENS = {
    ("NSE", "RELIANCE"): 2885,
    ("NSE", "TCS"): 11536,
    ("NSE", "INFY"): 11536,
    ("NSE", "HDFCBANK"): 12777,
    ("NSE", "ICICIBANK"): 11536,
    ("NSE", "SBIN"): 11536,
    ("NSE", "BHARTIARTL"): 11536,
    ("BSE", "500325"): 500325,  # BSE: scrip code = token
}


class AngelOneClient:
    """
    Direct HTTP client for Angel One Smart API.
    No SDK dependencies — uses pure requests + pyotp.
    Follows official API spec: https://smartapi.angelone.in/docs
    """
    
    BASE_URL = "https://apiconnect.angelone.in"
    
    def __init__(self):
        self.api_key = settings.angel_api_key
        self.client_code = settings.angel_client_code
        self.mpin = settings.angel_api_secret  # Your 4-digit MPIN
        self.totp_secret = settings.angel_totp_secret
        self.jwt_token = None
        self.refresh_token = None
        self.feed_token = None
        self.token_expiry = None  # Track token expiration
        self._public_ip = None
        self.last_error = None
        self._rate_limiter = RateLimiter(initial_delay=0.05, max_delay=5, max_retries=3)
    
    @property
    def public_ip(self):
        """Cache public IP to avoid repeated lookups"""
        if self._public_ip is None:
            try:
                self._public_ip = requests.get("https://api.ipify.org", timeout=5).text
            except (requests.RequestException, Exception) as e:
                logger.warning(f"Failed to fetch public IP: {e}, using fallback")
                self._public_ip = "127.0.0.1"
        return self._public_ip
    
    def _get_headers(self, include_auth: bool = True):
        """Build standard headers for Angel One API"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": self.public_ip,
            "X-MACAddress": "00:00:00:00:00:00",  # Dummy MAC (required by API)
            "X-PrivateKey": self.api_key,
        }
        if include_auth and self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        return headers
    
    def login(self, totp_code: str | None = None) -> bool:
        """
        Authenticate and obtain JWT token.
        Returns True if successful, False otherwise.
        """
        try:
            if totp_code:
                otp = totp_code.strip()
            elif self.totp_secret:
                otp = pyotp.TOTP(self.totp_secret).now()
            else:
                logger.error("❌ Login failed: TOTP code or secret is required")
                return False

            url = f"{self.BASE_URL}/rest/auth/angelbroking/user/v1/loginByPassword"

            payload = {
                "clientcode": self.client_code,
                "password": self.mpin,  # 4-digit MPIN (NOT API secret)
                "totp": otp,
            }
            
            resp = requests.post(
                url, 
                json=payload, 
                headers=self._get_headers(include_auth=False), 
                timeout=30
            )
            try:
                data = resp.json()
            except (ValueError, requests.exceptions.JSONDecodeError) as je:
                self.last_error = f"Invalid JSON response: {je}"
                logger.error(f"❌ Login error: {self.last_error}")
                return False
            
            if resp.status_code == 200 and data.get("status"):
                login_data = data["data"]
                self.jwt_token = login_data["jwtToken"]
                self.refresh_token = login_data.get("refreshToken")
                self.feed_token = login_data.get("feedToken") or self.jwt_token
                # Set token expiry to 2 hours from now (conservative estimate)
                self.token_expiry = datetime.now() + timedelta(hours=2)
                logger.info("✅ Angel One authenticated")
                self._rate_limiter.reset()
                return True
            else:
                self.last_error = data.get("message") or data.get("errorcode") or "Login failed"
                logger.error(f"❌ Login failed: {self.last_error}")
                return False
        except requests.RequestException as e:
            self.last_error = str(e)
            logger.error(f"❌ Login network error: {e}")
            return False
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"❌ Login error: {e}")
            return False
    
    def _ensure_token_valid(self) -> bool:
        """Ensure JWT token is valid, refresh if needed."""
        if not self.jwt_token:
            return self.login()
        
        # Check if token is expiring soon (within 5 minutes)
        if self.token_expiry and datetime.now() > self.token_expiry - timedelta(minutes=5):
            logger.info("Token expiring soon, attempting refresh...")
            if self.refresh_token:
                return self._refresh_token_internal()
            else:
                logger.warning("No refresh token available, re-authenticating...")
                return self.login()
        
        return True
    
    def _refresh_token_internal(self) -> bool:
        """Refresh JWT token using refresh token."""
        if not self.refresh_token:
            logger.warning("No refresh token available")
            return self.login()
        
        try:
            url = f"{self.BASE_URL}/rest/auth/angelbroking/user/v1/refreshToken"
            payload = {
                "refreshToken": self.refresh_token,
            }
            
            resp = requests.post(
                url,
                json=payload,
                headers=self._get_headers(include_auth=False),
                timeout=30
            )
            
            try:
                data = resp.json()
            except (ValueError, requests.exceptions.JSONDecodeError) as je:
                logger.error(f"Token refresh JSON parse error: {je}")
                return self.login()
            
            if resp.status_code == 200 and data.get("status"):
                token_data = data.get("data", {})
                self.jwt_token = token_data.get("jwtToken", self.jwt_token)
                self.refresh_token = token_data.get("refreshToken", self.refresh_token)
                self.feed_token = token_data.get("feedToken") or self.jwt_token
                self.token_expiry = datetime.now() + timedelta(hours=2)
                logger.info("✅ Token refreshed successfully")
                return True
            else:
                logger.warning("Token refresh failed, re-authenticating...")
                return self.login()
        except requests.RequestException as e:
            logger.error(f"Token refresh network error: {e}, falling back to login")
            return self.login()
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return self.login()
    
    def get_profile(self) -> dict | None:
        """Fetch connected Angel One profile details."""
        if not self._ensure_token_valid():
            return None

        try:
            url = f"{self.BASE_URL}/rest/secure/angelbroking/user/v1/getProfile"
            resp = requests.get(url, headers=self._get_headers(include_auth=True), timeout=10)
            try:
                data = resp.json()
            except (ValueError, requests.exceptions.JSONDecodeError) as je:
                logger.error(f"Profile JSON parse error: {je}")
                return None

            if resp.status_code == 200 and data.get("status") and data.get("data"):
                return data["data"]

            logger.warning(f"Profile failed: {data}")
            return None
        except requests.RequestException as e:
            logger.error(f"Profile network error: {e}")
            return None
        except Exception as e:
            logger.error(f"Profile error: {e}")
            return None

    def get_quote(
        self,
        symbol: str,
        exchange: str = "NSE",
        token: str | int | None = None,
        trading_symbol: str | None = None,
    ) -> dict | None:
        """
        Fetch real-time quote using ltpData endpoint.
        Includes rate limiting and automatic token refresh.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE", "500325")
            exchange: "NSE" or "BSE"
        
        Returns:
            dict with quote data or None if failed
        """
        if not self._ensure_token_valid():
            return None
        
        symbol = symbol.strip().upper()
        trading_symbol = (trading_symbol or symbol).strip().upper()

        # Get token from Angel master data first, then fallback map.
        token = token or ANGEL_TOKENS.get((exchange, symbol)) or ANGEL_TOKENS.get((exchange, trading_symbol))
        if not token and exchange == "BSE" and symbol.isdigit():
            token = int(symbol)  # BSE: scrip code = token
        if not token:
            logger.warning(f"No token found for {symbol} ({exchange})")
            return None
        
        # Attempt with rate limiting and retry logic
        limiter = RateLimiter(initial_delay=0.05, max_delay=5, max_retries=3)
        
        while True:
            try:
                url = f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/getLtpData"
                payload = {
                    "exchange": exchange,
                    "tradingsymbol": trading_symbol,
                    "symboltoken": str(token),
                }
                
                resp = requests.post(
                    url, 
                    json=payload, 
                    headers=self._get_headers(include_auth=True), 
                    timeout=10
                )
                
                # Check for rate limiting
                if limiter.should_retry(resp.status_code):
                    if limiter.retry_count < limiter.max_retries:
                        limiter.wait()
                        continue
                    else:
                        logger.error(f"Quote rate limited for {symbol}, max retries exceeded")
                        return None
                
                try:
                    data = resp.json()
                except (ValueError, requests.exceptions.JSONDecodeError) as je:
                    logger.error(f"Quote JSON parse error for {symbol}: {je}")
                    return None
                
                # ✅ FIX: Angel One ltpData returns "status": true (NOT "success")
                if resp.status_code == 200 and data.get("status") and data.get("data"):
                    d = data["data"]
                    try:
                        limiter.reset()  # Success, reset rate limiter
                        return {
                            "symbol": symbol,
                            "tradingsymbol": trading_symbol,
                            "token": str(token),
                            "exchange": exchange,
                            "price": float(d["ltp"]),
                            "change_pct": float(d.get("pChange", 0)),
                            "high": float(d["high"]),
                            "low": float(d["low"]),
                            "open": float(d["open"]),
                            "close": float(d["close"]),
                            "volume": int(d.get("volume", 0)),
                            "timestamp": d.get("lastUpdateTime"),
                        }
                    except (KeyError, ValueError, TypeError) as ve:
                        logger.error(f"Quote data conversion error for {symbol}: {ve}. Data: {d}")
                        return None
                else:
                    logger.warning(f"Quote failed for {symbol}: {data}")
                    # If token invalid (AG8001), clear JWT and retry login once
                    if data.get("errorCode") == "AG8001":
                        self.jwt_token = None
                        if self.login():
                            return self.get_quote(symbol, exchange)  # Retry once
                    return None
                    
            except requests.RequestException as e:
                if limiter.retry_count < limiter.max_retries:
                    logger.debug(f"Quote network error for {symbol}, retrying: {e}")
                    limiter.wait()
                    continue
                else:
                    logger.error(f"Quote network error for {symbol}, max retries exceeded: {e}")
                    return None
            except Exception as e:
                logger.error(f"Quote error for {symbol}: {e}")
                return None
    
    def get_historical_candles(
        self, 
        symbol: str, 
        exchange: str = "NSE",
        interval: str = "DAY",
        from_date: str = None,
        to_date: str = None
    ) -> list[dict] | None:
        """
        Fetch historical candlestick data.
        Note: For now, falls back to yfinance for historical data.
        """
        # TODO: Implement Angel One candleData endpoint
        # For now, return None to trigger yfinance fallback in data_engine.py
        logger.info(f"Historical data for {symbol} using fallback (yfinance)")
        return None
