# src/data_engine.py
import yfinance as yf
import pandas as pd
import logging
import re
from src.config import settings

# Optional Angel One import (only if configured)
try:
    from src.angel_client import AngelOneClient
    ANGEL_AVAILABLE = True
except ImportError:
    ANGEL_AVAILABLE = False

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


# =============================================================================
# Exchange Detection & Symbol Formatting
# =============================================================================

def _detect_exchange(ticker: str) -> str:
    """
    Detect exchange from ticker string.
    
    Rules:
    - Ends with .BO or is 6-digit numeric → BSE
    - Ends with .NS or anything else → NSE (default)
    
    Args:
        ticker: Raw ticker string (e.g., "RELIANCE", "500325", "TCS.BO")
    
    Returns:
        "NSE" or "BSE"
    """
    ticker_clean = ticker.strip().upper()

    if ticker_clean in {"^NSEI", "NIFTY", "NIFTY 50"}:
        return "NSE"
    if ticker_clean in {"^BSESN", "SENSEX"}:
        return "BSE"
    
    # Explicit suffix detection
    if ticker_clean.endswith(".BO"):
        return "BSE"
    if ticker_clean.endswith(".NS"):
        return "NSE"
    
    # BSE scrip codes are typically 6-digit numbers
    if re.match(r"^\d{6}$", ticker_clean):
        return "BSE"
    
    # Default to NSE for alphabetic symbols
    return "NSE"


def _format_symbol(ticker: str) -> str:
    """
    Format ticker with correct Yahoo Finance suffix.
    
    Args:
        ticker: Raw ticker (e.g., "RELIANCE", "500325", "TCS.BO")
    
    Returns:
        Formatted symbol for yfinance (e.g., "RELIANCE.NS", "500325.BO")
    """
    ticker_clean = ticker.strip().upper()

    if ticker_clean.startswith("^"):
        return ticker_clean
    if ticker_clean in {"NIFTY", "NIFTY 50"}:
        return "^NSEI"
    if ticker_clean == "SENSEX":
        return "^BSESN"
    
    # If already formatted, return as-is
    if ticker_clean.endswith(".NS") or ticker_clean.endswith(".BO"):
        return ticker_clean

    ticker_clean = ticker_clean.replace("-EQ", "")
    
    # Detect exchange and append suffix
    exchange = _detect_exchange(ticker_clean)
    suffix = ".BO" if exchange == "BSE" else ".NS"
    
    return f"{ticker_clean}{suffix}"


# =============================================================================
# Angel One Client Singleton (Lazy Initialization)
# =============================================================================

_angel_client = None

def _get_angel_client() -> AngelOneClient | None:
    """Get or create AngelOneClient singleton"""
    global _angel_client
    if not ANGEL_AVAILABLE:
        return None
    if _angel_client is None:
        _angel_client = AngelOneClient()
    return _angel_client


# =============================================================================
# Live Price Snapshot (Angel One → yfinance fallback)
# =============================================================================

def fetch_live_snapshot(ticker: str, exchange: str = None) -> dict | None:
    """
    Fetches real-time price snapshot for a given ticker.
    Priority: Angel One (if configured) → yfinance fallback
    
    Args:
        ticker: Stock symbol (e.g., "RELIANCE", "500325", "TCS.BO")
        exchange: Optional override ("NSE" or "BSE")
    
    Returns:
        dict with price data or None if fetch fails
    """
    # Determine exchange if not provided
    if exchange is None:
        exchange = _detect_exchange(ticker)
    
    # Try Angel One first if configured and available
    source = getattr(settings, 'data_source', 'yfinance').lower()
    if source == "angel_one" and ANGEL_AVAILABLE:
        client = _get_angel_client()
        if client and client.jwt_token:  # Only if already authenticated
            symbol_clean = re.sub(r'\.NS|\.BO', '', ticker.strip().upper())
            token = None
            trading_symbol = symbol_clean
            try:
                from src.angel_master import get_angel_master
                master = get_angel_master()
                if client.jwt_token and not master.jwt_token:
                    master.set_jwt_token(client.jwt_token)
                matches = master.search(symbol_clean.replace("-EQ", ""), limit=1, exchange=exchange)
                if matches:
                    match = matches[0]
                    token = match.get("token")
                    trading_symbol = match.get("tradingsymbol") or match.get("symbol") or symbol_clean
            except Exception as e:
                logger.debug(f"Failed to fetch Angel master token for {symbol_clean}: {e}")
                pass

            quote = client.get_quote(symbol_clean, exchange, token=token, trading_symbol=trading_symbol)
            if quote:
                return {
                    "Ticker": symbol_clean,
                    "Exchange": exchange,
                    "Price": quote["price"],
                    "Change_Pct": quote["change_pct"],
                    "High": quote["high"],
                    "Low": quote["low"],
                    "Volume": quote["volume"],
                    "Prev_Close": quote["close"],
                    "Open": quote["open"],
                }
            logger.warning(f"Angel One quote failed for {ticker}, falling back to yfinance")
    
    # Fallback to yfinance
    return _fetch_yfinance_snapshot(ticker, exchange)


def _fetch_yfinance_snapshot(ticker: str, exchange: str) -> dict | None:
    """Internal: Fetch snapshot via yfinance"""
    try:
        symbol = _format_symbol(ticker)
        stock = yf.Ticker(symbol)
        
        # Fetch 1-day history for OHLCV data
        hist = stock.history(period="1d", interval="1m")
        if hist.empty:
            hist = stock.history(period="1d", interval="1d")
            if hist.empty:
                return None
        
        last = hist.iloc[-1]
        
        # Get previous close from info or calculate from history
        info = stock.info
        prev_close = info.get('previousClose')
        if not prev_close and len(hist) > 1:
            prev_close = hist.iloc[-2]['Close']
        if not prev_close:
            prev_close = last.get('Open', last['Close'])
        
        # Calculate change percentage
        change_pct = ((last['Close'] - prev_close) / prev_close) * 100 if prev_close else 0
        
        return {
            "Ticker": ticker.strip().upper(),
            "Exchange": exchange,
            "Price": round(float(last['Close']), 2),
            "Change_Pct": round(float(change_pct), 2),
            "High": round(float(last['High']), 2),
            "Low": round(float(last['Low']), 2),
            "Volume": int(last.get('Volume', 0)),
            "Prev_Close": round(float(prev_close), 2),
            "Open": round(float(last.get('Open', prev_close)), 2)
        }
    except Exception as e:
        logger.error(f"Failed to fetch yfinance snapshot for {ticker}: {e}")
        return None


# =============================================================================
# Historical Candles (Angel One → yfinance fallback)
# =============================================================================

def fetch_historical_candles(
    ticker: str, 
    period: str = "3mo", 
    interval: str = "1d",
    exchange: str = None
) -> pd.DataFrame:
    """
    Fetches historical OHLCV candlestick data for technical analysis.
    Priority: Angel One (if configured) → yfinance fallback
    
    Args:
        ticker: Stock symbol (e.g., "RELIANCE", "500325")
        period: yfinance period string ('1d', '5d', '1mo', '3mo', '1y', etc.)
        interval: yfinance interval string ('1m', '5m', '1h', '1d', etc.)
        exchange: Optional override ("NSE" or "BSE")
    
    Returns:
        pd.DataFrame with columns: date, open, high, low, close, volume
        Empty DataFrame if fetch fails
    """
    if exchange is None:
        exchange = _detect_exchange(ticker)
    
    # Try Angel One first if configured (currently falls back to yfinance for history)
    source = getattr(settings, 'data_source', 'yfinance').lower()
    if source == "angel_one" and ANGEL_AVAILABLE:
        # TODO: Implement Angel One candleData endpoint when ready
        # For now, log and fall through to yfinance
        logger.info(f"Using yfinance for historical data: {ticker} ({exchange})")
    
    # Fallback to yfinance (reliable for historical data)
    return _fetch_yfinance_history(ticker, period, interval, exchange)


def _fetch_yfinance_history(
    ticker: str, 
    period: str, 
    interval: str,
    exchange: str
) -> pd.DataFrame:
    """Internal: Fetch historical data via yfinance"""
    try:
        symbol = _format_symbol(ticker)
        stock = yf.Ticker(symbol)
        
        # Fetch historical data
        df = stock.history(period=period, interval=interval)
        
        if df.empty:
            logger.warning(f"No historical data found for {symbol}")
            return pd.DataFrame()
        
        # Standardize column names to lowercase for pandas-ta compatibility
        df.columns = [col.lower() for col in df.columns]
        
        # Ensure 'date' is a column, not index
        df.reset_index(inplace=True)
        
        # Handle case where date column has different name
        if 'date' not in df.columns:
            date_col = [c for c in df.columns if 'date' in c.lower()][0]
            df.rename(columns={date_col: 'date'}, inplace=True)
        
        # Ensure numeric columns are proper types
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop rows with missing critical data
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch yfinance history for {ticker}: {e}")
        return pd.DataFrame()


# =============================================================================
# Stock Metadata & Validation Helpers
# =============================================================================

def get_stock_info(ticker: str, exchange: str = None) -> dict | None:
    """
    Fetches comprehensive stock metadata from Yahoo Finance.
    
    Args:
        ticker: Stock symbol
        exchange: Optional override ("NSE" or "BSE")
    
    Returns:
        dict with company info or None if fetch fails
    """
    if exchange is None:
        exchange = _detect_exchange(ticker)
    
    try:
        symbol = _format_symbol(ticker)
        stock = yf.Ticker(symbol)
        info = stock.info
        
        if not info:
            return None
        
        return {
            "symbol": ticker.strip().upper(),
            "exchange": exchange,
            "name": info.get('longName', info.get('shortName', ticker)),
            "sector": info.get('sector', 'Unknown'),
            "industry": info.get('industry', 'Unknown'),
            "market_cap": info.get('marketCap'),
            "pe_ratio": info.get('trailingPE'),
            "dividend_yield": info.get('dividendYield'),
            "52w_high": info.get('fiftyTwoWeekHigh'),
            "52w_low": info.get('fiftyTwoWeekLow'),
            "avg_volume": info.get('averageVolume'),
            "currency": info.get('currency', 'INR')
        }
    except Exception as e:
        logger.error(f"Failed to fetch stock info for {ticker}: {e}")
        return None


def validate_ticker(ticker: str, exchange: str = None) -> bool:
    """
    Quick validation: checks if ticker has any price data available.
    
    Args:
        ticker: Stock symbol to validate
        exchange: Optional override ("NSE" or "BSE")
    
    Returns:
        True if ticker appears valid, False otherwise
    """
    try:
        symbol = _format_symbol(ticker)
        stock = yf.Ticker(symbol)
        hist = stock.history(period="5d", interval="1d")
        return not hist.empty
    except:
        return False


# =============================================================================
# Utility: Batch Fetch for Screener Optimization
# =============================================================================

def fetch_batch_quotes(tickers: list[str]) -> dict[str, dict]:
    """
    Fetch live snapshots for multiple tickers with basic rate limiting.
    
    Args:
        tickers: List of ticker symbols
    
    Returns:
        Dict mapping ticker → quote data (or None if failed)
    """
    import time
    
    results = {}
    for idx, ticker in enumerate(tickers):
        # Small delay to avoid rate limiting
        if idx > 0:
            time.sleep(0.1)
        
        results[ticker] = fetch_live_snapshot(ticker)
    
    return results
