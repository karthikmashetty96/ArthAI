"""
Dynamic NSE+BSE Stock Universe Fetcher
- No API keys required
- Uses official public endpoints
- Local caching for performance
"""
import httpx
import pandas as pd
import logging
from pathlib import Path
from diskcache import Cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Local cache directory (gitignored)
CACHE_DIR = Path("data/cache/stock_universe")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
cache = Cache(str(CACHE_DIR))

# Public endpoints (no auth)
NSE_EQUITY_CSV = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
BSE_STOCK_API = "https://api.bseindia.com/BseIndiaAPI/api/StockReach/v1/stockreach"

def _fetch_nse_stocks() -> list[dict]:
    """Fetch NSE equity list from official CSV endpoint."""
    try:
        with httpx.Client(timeout=30) as client:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = client.get(NSE_EQUITY_CSV, headers=headers)
            response.raise_for_status()
            
            df = pd.read_csv(pd.io.common.BytesIO(response.content))
            # Keep only active, equity stocks
            df = df[df["SERIES"] == "EQ"]
            
            return [
                {
                    "symbol": row["SYMBOL"],
                    "name": row["NAME OF COMPANY"],
                    "exchange": "NSE",
                    "sector": row.get("INDUSTRY", "Unknown")
                }
                for _, row in df.iterrows()
            ]
    except httpx.TimeoutException as e:
        logger.error(f"NSE timeout: {e}, retrying with longer timeout...")
        try:
            with httpx.Client(timeout=60) as client:
                response = client.get(NSE_EQUITY_CSV, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
                df = pd.read_csv(pd.io.common.BytesIO(response.content))
                df = df[df["SERIES"] == "EQ"]
                return [{"symbol": row["SYMBOL"], "name": row["NAME OF COMPANY"], "exchange": "NSE", "sector": row.get("INDUSTRY", "Unknown")} for _, row in df.iterrows()]
        except Exception as retry_e:
            logger.error(f"NSE fetch failed after retry: {retry_e}")
            return []
    except Exception as e:
        logger.error(f"Failed to fetch NSE stocks: {e}")
        return []

def _fetch_bse_stocks() -> list[dict]:
    """Fetch BSE stock list via public API endpoint."""
    try:
        with httpx.Client(timeout=30) as client:
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
            # BSE endpoint returns top 500 by default; we can paginate if needed
            response = client.get(
                BSE_STOCK_API,
                headers=headers,
                params={"scripcode": "", "pageNo": 1, "pageSize": 500}
            )
            response.raise_for_status()
            data = response.json()
            
            stocks = []
            for item in data.get("data", []):
                stocks.append({
                    "symbol": item.get("scripcode", ""),
                    "name": item.get("scripname", ""),
                    "exchange": "BSE",
                    "sector": item.get("industry", "Unknown")
                })
            return stocks
    except httpx.TimeoutException as e:
        logger.error(f"BSE timeout: {e}, retrying with longer timeout...")
        try:
            with httpx.Client(timeout=60) as client:
                response = client.get(BSE_STOCK_API, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}, params={"scripcode": "", "pageNo": 1, "pageSize": 500})
                response.raise_for_status()
                data = response.json()
                return [{"symbol": item.get("scripcode", ""), "name": item.get("scripname", ""), "exchange": "BSE", "sector": item.get("industry", "Unknown")} for item in data.get("data", [])]
        except Exception as retry_e:
            logger.error(f"BSE fetch failed after retry: {retry_e}")
            return []
    except Exception as e:
        logger.error(f"Failed to fetch BSE stocks: {e}")
        return []

def fetch_all_stocks(refresh: bool = False) -> list[dict]:
    """
    Fetch combined NSE+BSE stock list with local caching.
    
    Args:
        refresh: Force re-fetch from APIs (default: use cache if <24h old)
    
    Returns:
        List of dicts: [{"symbol": "RELIANCE", "name": "...", "exchange": "NSE"}, ...]
    """
    cache_key = "all_stocks_v1"
    
    # Return cached data if fresh (<24 hours) and not forcing refresh
    if not refresh and cache_key in cache:
        cached_data, timestamp = cache.get(cache_key)
        if datetime.now() - timestamp < timedelta(hours=24):
            logger.info("Using cached stock list")
            return cached_data
    
    # Fetch fresh data
    logger.info("Fetching fresh stock lists from NSE+BSE...")
    nse_stocks = _fetch_nse_stocks()
    bse_stocks = _fetch_bse_stocks()
    
    # Combine and deduplicate by symbol+exchange
    all_stocks = []
    seen = set()
    for stock in nse_stocks + bse_stocks:
        key = (stock["symbol"], stock["exchange"])
        if key not in seen:
            seen.add(key)
            all_stocks.append(stock)
    
    # Cache for 24 hours
    cache.set(cache_key, (all_stocks, datetime.now()), expire=86400)
    
    logger.info(f"Fetched {len(all_stocks)} unique stocks ({len(nse_stocks)} NSE, {len(bse_stocks)} BSE)")
    return all_stocks

def search_stocks(query: str, limit: int = 50) -> list[dict]:
    """
    Search stocks by symbol or name (case-insensitive).
    
    Args:
        query: Search term (e.g., "reliance", "bank", "TCS")
        limit: Max results to return
    
    Returns:
        Filtered list of matching stocks
    """
    if not query or len(query) < 2:
        return []
    
    all_stocks = fetch_all_stocks()
    query_lower = query.lower()
    
    matches = [
        stock for stock in all_stocks
        if query_lower in stock["symbol"].lower() 
        or query_lower in stock["name"].lower()
    ]
    
    # Sort: exact symbol match first, then name match
    def sort_key(s):
        symbol_match = int(s["symbol"].lower() == query_lower)
        name_match = int(query_lower in s["name"].lower())
        return (-symbol_match, -name_match, s["symbol"])
    
    return sorted(matches, key=sort_key)[:limit]