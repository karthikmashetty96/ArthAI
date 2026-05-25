"""
Cache manager for historical data and screening results.
Uses diskcache for persistent, efficient storage.
"""

import logging
from pathlib import Path
from datetime import datetime, timedelta
from diskcache import Cache
import pandas as pd

logger = logging.getLogger(__name__)

# Cache directory
CACHE_DIR = Path("data/cache/screener")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
cache = Cache(str(CACHE_DIR))

# Cache TTLs (in seconds)
HISTORICAL_DATA_TTL = 86400 * 7  # 7 days
SCREENER_RESULTS_TTL = 3600      # 1 hour
QUOTE_DATA_TTL = 300              # 5 minutes


def cache_key_for_historical(ticker: str, interval: str = "1d") -> str:
    """Generate cache key for historical OHLCV data."""
    return f"hist_{ticker}_{interval}".lower()


def cache_key_for_screener(query_hash: str) -> str:
    """Generate cache key for screener results."""
    return f"screen_{query_hash}"


def get_cached_historical(ticker: str, interval: str = "1d") -> pd.DataFrame | None:
    """Fetch cached historical data if available and fresh."""
    key = cache_key_for_historical(ticker, interval)
    try:
        if key in cache:
            data, timestamp = cache.get(key)
            if datetime.now() - timestamp < timedelta(seconds=HISTORICAL_DATA_TTL):
                logger.debug(f"Cache hit for historical {ticker}")
                return data
            else:
                del cache[key]  # Expired
    except Exception as e:
        logger.debug(f"Cache read error for {ticker}: {e}")
    return None


def set_cached_historical(ticker: str, data: pd.DataFrame, interval: str = "1d") -> bool:
    """Cache historical data."""
    key = cache_key_for_historical(ticker, interval)
    try:
        cache.set(key, (data, datetime.now()), expire=HISTORICAL_DATA_TTL)
        logger.debug(f"Cached historical data for {ticker}")
        return True
    except Exception as e:
        logger.warning(f"Failed to cache historical {ticker}: {e}")
        return False


def get_cached_screener_results(query_hash: str) -> list[dict] | None:
    """Fetch cached screener results if available and fresh."""
    key = cache_key_for_screener(query_hash)
    try:
        if key in cache:
            results, timestamp = cache.get(key)
            if datetime.now() - timestamp < timedelta(seconds=SCREENER_RESULTS_TTL):
                logger.debug(f"Cache hit for screener results")
                return results
            else:
                del cache[key]  # Expired
    except Exception as e:
        logger.debug(f"Cache read error for screener: {e}")
    return None


def set_cached_screener_results(query_hash: str, results: list[dict]) -> bool:
    """Cache screener results."""
    key = cache_key_for_screener(query_hash)
    try:
        cache.set(key, (results, datetime.now()), expire=SCREENER_RESULTS_TTL)
        logger.debug(f"Cached screener results ({len(results)} items)")
        return True
    except Exception as e:
        logger.warning(f"Failed to cache screener results: {e}")
        return False


def clear_screener_cache():
    """Clear all screener cache entries."""
    try:
        for key in list(cache.keys()):
            if str(key).startswith("screen_"):
                del cache[key]
        logger.info("Cleared screener cache")
    except Exception as e:
        logger.warning(f"Error clearing screener cache: {e}")


def cache_stats() -> dict:
    """Get cache statistics."""
    try:
        return {
            "size_mb": cache.volume() / (1024 * 1024),
            "items": len(cache),
        }
    except Exception:
        return {"size_mb": 0, "items": 0}
