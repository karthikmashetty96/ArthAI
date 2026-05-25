# src/angel_master.py
import requests
import json
import logging
import time
from pathlib import Path
from src.config import settings

logger = logging.getLogger(__name__)

# Cache settings
CACHE_FILE = Path("data/cache/angel_master.json")
CACHE_EXPIRY_SECONDS = 86400  # 24 hours
PUBLIC_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

INDEX_INSTRUMENTS = [
    {
        "symbol": "NIFTY",
        "tradingsymbol": "NIFTY",
        "name": "Nifty 50",
        "exch": "NSE",
        "token": "99926000",
        "instrumenttype": "INDEX",
        "segment": "INDEX",
    },
    {
        "symbol": "SENSEX",
        "tradingsymbol": "SENSEX",
        "name": "Sensex",
        "exch": "BSE",
        "token": "99919000",
        "instrumenttype": "INDEX",
        "segment": "INDEX",
    },
]

class AngelMaster:
    """Fetch and cache Angel One Master Contract List for search"""
    
    BASE_URL = "https://apiconnect.angelone.in"
    
    def __init__(self):
        self.api_key = settings.angel_api_key
        self.jwt_token = None
        self._public_ip = None
        self._master_list = None
        self._search_index = {}

    def _normalize_instrument(self, inst: dict) -> dict:
        """Normalize Angel master rows across endpoint/schema variants."""
        exch = inst.get("exch") or inst.get("exch_seg") or inst.get("exchange") or ""
        symbol = inst.get("symbol") or inst.get("tradingsymbol") or inst.get("name") or ""
        trading_symbol = inst.get("tradingsymbol") or symbol
        name = inst.get("name") or inst.get("symbol") or trading_symbol
        instrument_type = inst.get("instrumenttype") or inst.get("instrument_type") or ""

        return {
            **inst,
            "symbol": str(symbol).upper(),
            "tradingsymbol": str(trading_symbol).upper(),
            "name": str(name),
            "exch": str(exch).upper(),
            "token": str(inst.get("token", "")),
            "instrumenttype": str(instrument_type).upper(),
        }

    def _normalize_master_list(self, instruments: list[dict]) -> list[dict]:
        normalized = [self._normalize_instrument(inst) for inst in instruments if isinstance(inst, dict)]
        existing = {
            (inst.get("exch"), inst.get("tradingsymbol"), inst.get("token"))
            for inst in normalized
        }
        for index in INDEX_INSTRUMENTS:
            key = (index["exch"], index["tradingsymbol"], index["token"])
            if key not in existing:
                normalized.append(index.copy())
        return normalized
    
    @property
    def public_ip(self):
        """Cache public IP"""
        if self._public_ip is None:
            try:
                self._public_ip = requests.get("https://api.ipify.org", timeout=5).text
            except (requests.RequestException, Exception) as e:
                logger.warning(f"Failed to fetch public IP: {e}, using fallback")
                self._public_ip = "127.0.0.1"
        return self._public_ip
    
    def _get_headers(self, include_auth: bool = True):
        """Build standard Angel One headers"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": self.public_ip,
            "X-MACAddress": "00:00:00:00:00:00",
            "X-PrivateKey": self.api_key,
        }
        if include_auth and self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        return headers
    
    def set_jwt_token(self, token: str):
        """Set JWT token after successful login"""
        self.jwt_token = token
    
    def _load_from_cache(self) -> list | None:
        """Load master list from cache if valid"""
        if not CACHE_FILE.exists():
            return None
        
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
            
            # Check expiry
            if time.time() - data.get("timestamp", 0) < CACHE_EXPIRY_SECONDS:
                logger.info("✅ Loaded master list from cache")
                return self._normalize_master_list(data.get("data") or [])
            else:
                logger.info("⏰ Cache expired, will refresh")
                return None
        except Exception as e:
            logger.warning(f"⚠️ Cache load failed: {e}")
            return None
    
    def _save_to_cache(self, data: list):
        """Save master list to cache"""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump({
                    "timestamp": time.time(),
                    "data": data
                }, f)
            logger.info(f"✅ Cached {len(data)} instruments")
        except Exception as e:
            logger.error(f"❌ Cache save failed: {e}")
    
    def fetch_master_list(self, force_refresh: bool = False) -> list[dict]:
        """
        Fetch master contract list from Angel One API.
        
        Args:
            force_refresh: Skip cache and fetch fresh from API
            
        Returns:
            List of instrument dicts with symbol, name, exchange, token, etc.
        """
        # Try cache first
        if not force_refresh:
            cached = self._load_from_cache()
            if cached:
                return cached
        
        # Fetch from authenticated API first when available.
        try:
            if self.jwt_token:
                url = f"{self.BASE_URL}/rest/secure/angelbroking/master/v1/getMasterList"
                resp = requests.get(url, headers=self._get_headers(include_auth=True), timeout=60)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") and data.get("data"):
                        instruments = self._normalize_master_list(data["data"])
                        self._save_to_cache(instruments)
                        logger.info(f"✅ Fetched {len(instruments)} instruments from API")
                        return instruments
                    logger.error(f"❌ API error: {data}")
                else:
                    logger.error(f"❌ HTTP {resp.status_code}: {resp.text}")

            resp = requests.get(PUBLIC_MASTER_URL, timeout=60)
            if resp.status_code == 200:
                instruments = self._normalize_master_list(resp.json())
                self._save_to_cache(instruments)
                logger.info(f"✅ Fetched {len(instruments)} instruments from public master")
                return instruments
            logger.error(f"❌ Public master HTTP {resp.status_code}: {resp.text[:200]}")
                
        except Exception as e:
            logger.error(f"❌ Fetch error: {e}")
        
        # Fallback: return cached data even if expired
        fallback = self._load_from_cache()
        if fallback:
            logger.warning("⚠️ Using expired cache as fallback")
            return fallback
        
        return []
    
    def _build_search_index(self, instruments: list[dict]):
        """Build inverted index for fast fuzzy search"""
        self._search_index = {
            "symbols": {},  # symbol -> instrument
            "names": {},    # lowercase name words -> [instruments]
            "tokens": {},   # token -> instrument
        }
        
        for inst in instruments:
            # Index by symbol
            sym = inst.get("symbol", "").upper()
            if sym:
                self._search_index["symbols"][sym] = inst

            trading_symbol = inst.get("tradingsymbol", "").upper()
            if trading_symbol:
                self._search_index["symbols"][trading_symbol] = inst
            
            # Index by name words (fuzzy)
            name = inst.get("name", "").lower()
            for word in name.replace(" ltd", "").replace(" limited", "").split():
                if len(word) >= 2:  # Skip short words
                    if word not in self._search_index["names"]:
                        self._search_index["names"][word] = []
                    self._search_index["names"][word].append(inst)
            
            # Index by token (for BSE numeric searches)
            token = inst.get("token", "")
            if token:
                self._search_index["tokens"][str(token)] = inst
    
    def search(self, query: str, limit: int = 50, exchange: str = None) -> list[dict]:
        """
        Search instruments by symbol, name, or token.
        
        Args:
            query: Search string (e.g., "rel", "bank", "500325")
            limit: Max results to return
            exchange: Optional filter: "NSE" or "BSE"
            
        Returns:
            List of matching instruments
        """
        if not self._master_list:
            self._master_list = self.fetch_master_list()
        if "symbols" not in self._search_index:
            self._build_search_index(self._master_list)
        
        if not self._master_list:
            return []
        
        query = query.strip().upper()
        results = []
        seen = set()
        
        # 1. Exact symbol match (highest priority)
        if query in self._search_index["symbols"]:
            inst = self._search_index["symbols"][query]
            if not exchange or inst.get("exch") == exchange:
                results.append(inst)
                seen.add(inst.get("token"))
        
        # 2. Exact token match (for BSE numeric codes)
        if query in self._search_index["tokens"]:
            inst = self._search_index["tokens"][query]
            if inst.get("token") not in seen:
                if not exchange or inst.get("exch") == exchange:
                    results.append(inst)
                    seen.add(inst.get("token"))
        
        # 3. Startswith symbol match
        if len(query) >= 2:
            for sym, inst in self._search_index["symbols"].items():
                if sym.startswith(query) and inst.get("token") not in seen:
                    if not exchange or inst.get("exch") == exchange:
                        results.append(inst)
                        seen.add(inst.get("token"))
                        if len(results) >= limit:
                            break
        
        # 4. Fuzzy name match (if still need more results)
        if len(results) < limit and len(query) >= 2:
            query_lower = query.lower()
            for word, insts in self._search_index["names"].items():
                if query_lower in word or word.startswith(query_lower):
                    for inst in insts:
                        if inst.get("token") not in seen:
                            if not exchange or inst.get("exch") == exchange:
                                results.append(inst)
                                seen.add(inst.get("token"))
                                if len(results) >= limit:
                                    break
                    if len(results) >= limit:
                        break
        
        # Sort: exact matches first, then by symbol
        def sort_key(inst):
            is_exact = inst.get("symbol", "").upper() == query
            return (0 if is_exact else 1, inst.get("symbol", ""))
        
        results.sort(key=sort_key)
        return results[:limit]

    def get_equities(self, exchange: str = None) -> list[dict]:
        """Get all NSE/BSE equity rows from the Angel master list."""
        instruments = self.get_all_symbols(exchange=exchange)
        equities = []
        for inst in instruments:
            exch = inst.get("exch")
            instrument_type = inst.get("instrumenttype", "")
            symbol = inst.get("symbol", "")
            trading_symbol = inst.get("tradingsymbol", "")
            name = inst.get("name", "")
            lotsize = str(inst.get("lotsize", ""))
            if exch not in {"NSE", "BSE"}:
                continue
            if instrument_type not in {"", "EQ"}:
                continue

            if exch == "NSE":
                is_equity = (
                    (trading_symbol.endswith("-EQ") or symbol.endswith("-EQ"))
                    and "INAV" not in name
                    and "INAV" not in symbol
                )
            else:
                # BSE rows share blank instrumenttype for many asset classes.
                # Listed equities use alpha symbols and lotsize 1; debt/bonds
                # usually contain digits and/or larger lot sizes.
                is_equity = (
                    bool(symbol)
                    and symbol.replace("&", "").replace("-", "").isalpha()
                    and lotsize in {"1", "1.0"}
                )
            if is_equity:
                equities.append(inst)
        return sorted(equities, key=lambda i: (i.get("exch", ""), i.get("symbol", "")))

    def get_indexes(self) -> list[dict]:
        """Get Nifty/Sensex index instruments."""
        instruments = self.get_all_symbols()
        wanted = {"NIFTY", "NIFTY 50", "SENSEX"}
        indexes = [
            inst for inst in instruments
            if inst.get("instrumenttype") == "INDEX"
            and (inst.get("symbol") in wanted or inst.get("name", "").upper() in wanted)
        ]
        if not indexes:
            indexes = [index.copy() for index in INDEX_INSTRUMENTS]
        return indexes
    
    def get_all_symbols(self, exchange: str = None) -> list[dict]:
        """Get all symbols, optionally filtered by exchange"""
        if not self._master_list:
            self._master_list = self.fetch_master_list()
        
        if exchange:
            return [i for i in self._master_list if i.get("exch") == exchange]
        return self._master_list or []


# Singleton instance
_angel_master = None

def get_angel_master() -> AngelMaster:
    """Get or create AngelMaster singleton"""
    global _angel_master
    if _angel_master is None:
        _angel_master = AngelMaster()
    return _angel_master
