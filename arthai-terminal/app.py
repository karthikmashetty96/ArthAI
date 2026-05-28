# app.py - Professional UI with Angel One Smart API Integration
import sys
import os
from datetime import datetime
# import re  # removed unused import
import pandas as pd
import streamlit as st
import yfinance as yf
# from datetime import datetime  # removed unused import

# Import Core Modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from src.data_engine import fetch_live_snapshot, fetch_historical_candles
from src.indicators import calculate_technical_indicators, check_screener_rules
from src.ai_reasoning import generate_ai_trade_plan
from src.notifier import send_telegram_alert
from src.config import settings
from src.angel_master import get_angel_master  # NEW: Angel One master list
from src.angel_stream import stream_store
from src.screener import (
    condition_passes,
    fetch_screener_metrics,
    metrics_to_display_row,
    parse_screener_query,
)
from components.sidebar_controls import render_sidebar
from components.data_grid import render_data_grid
from components.candlestick_chart import render_chart
from components.ai_panel import render_ai_panel
from components.paper_trading import render_paper_trading
from components.algo_lab import render_algo_lab

DEFAULT_SCREENER_QUERY = """Market Capitalization > 500 AND
Market Capitalization < 15000 AND
Current price > 100 AND
Current price > DMA 50 AND
DMA 50 > DMA 200 AND
RSI > 55 AND
RSI < 70 AND
Current price < 1.25 * DMA 50 AND
Sales growth 3Years > 15 AND
Profit growth 3Years > 15 AND
YOY Quarterly profit growth > 25 AND
YOY Quarterly sales growth > 15 AND
Debt to equity < 0.5 AND
Return on capital employed > 15 AND
Promoter holding > 40 AND
Volume > 150000"""

# =============================================================================
# 🎨 Professional Page Configuration
# =============================================================================
st.set_page_config(
    page_title="ArthAI Terminal",
    page_icon="AI",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/arthai-terminal',
        'Report a bug': 'https://github.com/yourusername/arthai-terminal/issues',
        'About': "# ArthAI Terminal\nLocal AI-Powered NSE/BSE Stock Screener"
    }
)

# =============================================================================
# 🎨 Professional CSS Theme (NSE-Inspired: Saffron, White, Green)
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    :root {
        --bg: var(--background-color, #060913);
        --surface: var(--secondary-background-color, rgba(15, 23, 42, 0.4));
        --border: rgba(128, 128, 128, 0.15);
        --text: var(--text-color, #f8fafc);
        --muted: #64748b;
        --brand: var(--primary-color, #06b6d4);
        --brand-gradient: linear-gradient(135deg, #06b6d4 0%, #10b981 100%);
        --brand-soft: rgba(6, 182, 212, 0.12);
        --positive: #10b981;
        --negative: #f43f5e;
    }

    html, body, [class*="css"] {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    .stApp {
        color: var(--text);
    }

    .block-container {
        max-width: 1550px;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    /* Floating Glass Header */
    .main-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
        background: rgba(128, 128, 128, 0.08) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(20px);
    }

    .brand-wrap {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .brand-mark {
        width: 48px;
        height: 48px;
        border-radius: 12px;
        display: grid;
        place-items: center;
        background: var(--brand-gradient);
        color: #ffffff !important;
        font-size: 1rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        box-shadow: 0 0 25px rgba(6, 182, 212, 0.25);
    }

    .header-title {
        margin: 0;
        color: var(--text) !important;
        font-size: 1.6rem;
        line-height: 1.1;
        font-weight: 800;
        letter-spacing: -0.02em;
    }

    .header-subtitle {
        margin: 0.25rem 0 0;
        color: var(--muted);
        font-size: 0.9rem;
        font-weight: 500;
    }

    .header-status {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.85rem;
        background: var(--brand-soft);
        color: var(--brand) !important;
        border: 1px solid rgba(6, 182, 212, 0.25);
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 700;
        white-space: nowrap;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background: var(--positive);
        border-radius: 999px;
        box-shadow: 0 0 12px var(--positive);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    /* Glass Cards */
    .glass-card {
        background: rgba(128, 128, 128, 0.08) !important;
        backdrop-filter: blur(16px);
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06) !important;
        padding: 1.25rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .glass-card:hover {
        border-color: var(--brand) !important;
        box-shadow: 0 15px 35px rgba(6, 182, 212, 0.1) !important;
    }

    /* High-Tech Metrics styling */
    [data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.06) !important;
        backdrop-filter: blur(12px);
        border: 1px solid var(--border) !important;
        border-radius: 12px;
        padding: 0.85rem 1rem !important;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.03) !important;
        transition: border-color 0.2s;
    }
    
    [data-testid="stMetric"]:hover {
        border-color: var(--brand) !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    [data-testid="stMetricValue"] {
        color: var(--text) !important;
        font-size: 1.3rem !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    [data-testid="stMetricDelta"] {
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Custom borders and outlines */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05) !important;
        background: rgba(128, 128, 128, 0.04) !important;
        backdrop-filter: blur(14px);
    }

    /* Sidebar controls */
    section[data-testid="stSidebar"] {
        border-right: 1px solid var(--border) !important;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: var(--text) !important;
        letter-spacing: -0.01em;
    }

    /* Futuristic Buttons */
    .stButton > button,
    button[kind="primary"] {
        border: none !important;
        background: var(--brand-gradient) !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        border-radius: 10px !important;
        letter-spacing: 0.02em !important;
        padding: 0.6rem 1.5rem !important;
        box-shadow: 0 4px 15px rgba(6, 182, 212, 0.2) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .stButton > button:hover,
    button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3) !important;
    }

    button[kind="secondary"] {
        background: rgba(128, 128, 128, 0.05) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    button[kind="secondary"]:hover {
        background: rgba(128, 128, 128, 0.1) !important;
        border-color: var(--brand) !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        padding: 0.4rem;
        background: rgba(128, 128, 128, 0.06) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 0.75rem 1.25rem !important;
        color: var(--muted) !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s !important;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(128, 128, 128, 0.15) !important;
        color: var(--brand) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05) !important;
        border-bottom: 2px solid var(--brand) !important;
    }

    /* DataFrame custom overrides */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05) !important;
    }

    /* Glowing alert custom borders */
    .stAlert {
        border-radius: 12px !important;
        background-color: rgba(128, 128, 128, 0.08) !important;
        border: 1px solid var(--border) !important;
        backdrop-filter: blur(10px);
    }
    
    .stAlert [data-testid="stNotificationContentSuccess"] {
        border-left: 4px solid var(--positive) !important;
    }
    .stAlert [data-testid="stNotificationContentError"] {
        border-left: 4px solid var(--negative) !important;
    }

    /* custom badge */
    .pro-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.02em;
    }
    
    .badge-buy {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-sell {
        background: rgba(244, 63, 94, 0.15);
        color: #fb7185;
        border: 1px solid rgba(244, 63, 94, 0.3);
    }

    h1, h2, h3 {
        color: var(--text) !important;
        letter-spacing: -0.01em;
        font-weight: 700 !important;
    }

    /* Scrollbars */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(128, 128, 128, 0.03);
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(128, 128, 128, 0.15);
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--brand);
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <div class="brand-wrap">
        <div class="brand-mark">ARTH</div>
        <div>
            <h1 class="header-title">ArthAI Trading Terminal</h1>
            <p class="header-subtitle">Live market watch · Screener radar · AI trade desk · Simulated execution</p>
        </div>
    </div>
    <div class="header-status">
        <div class="status-dot"></div>
        <span>LIVE DATA ENGINE</span>
    </div>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# 🧩 Helper Components
# =============================================================================

def render_status_indicator(status: str, message: str):
    """Render status with native Streamlit alerts."""
    if status == "success":
        st.success(message)
    elif status == "warning":
        st.warning(message)
    elif status == "error":
        st.error(message)
    else:
        st.info(message)


def render_metric_card(label: str, value: str, trend: str = None, positive: bool = None):
    """Render a compact native metric."""
    delta = None
    if trend:
        delta = "Up" if positive else "Down"
    st.metric(label, value, delta=delta)


def render_alert_badge(text: str, alert_type: str):
    """Return plain signal text for table display."""
    return text


def _format_inr(value, fallback: str = "N/A") -> str:
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return fallback


def _format_volume(value) -> str:
    try:
        volume = float(value or 0)
    except (TypeError, ValueError):
        return "0"
    if volume >= 10_000_000:
        return f"{volume / 10_000_000:.2f} Cr"
    if volume >= 100_000:
        return f"{volume / 100_000:.2f} L"
    return f"{volume:,.0f}"


def _now_label() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _quote_values(quote: dict, title: str | None = None) -> dict:
    symbol = title or quote.get("symbol") or quote.get("Ticker") or "UNKNOWN"
    exchange = quote.get("exchange") or quote.get("Exchange") or ""
    price = quote.get("price", quote.get("Price"))
    change_pct = float(quote.get("change_pct", quote.get("Change_Pct", 0)) or 0)
    high = quote.get("high", quote.get("High"))
    low = quote.get("low", quote.get("Low"))
    volume = quote.get("volume", quote.get("Volume"))
    return {
        "symbol": symbol,
        "exchange": exchange,
        "price": price,
        "change_pct": change_pct,
        "high": high,
        "low": low,
        "volume": volume,
    }


def render_quote_tile(quote: dict, title: str | None = None):
    values = _quote_values(quote, title)
    with st.container(border=True):
        top_left, top_right = st.columns([1.4, 1])
        with top_left:
            st.caption(values["exchange"] or "Market")
            st.subheader(values["symbol"])
        with top_right:
            st.metric(
                "Change",
                f"{values['change_pct']:+.2f}%",
                delta=f"{values['change_pct']:+.2f}%",
            )
        st.metric("LTP", _format_inr(values["price"]))
        low_col, high_col, vol_col = st.columns(3)
        low_col.caption(f"Low {_format_inr(values['low'], '-')}")
        high_col.caption(f"High {_format_inr(values['high'], '-')}")
        vol_col.caption(f"Vol {_format_volume(values['volume'])}")


def _quote_from_tick(stock: dict, tick: dict | None) -> dict | None:
    if not tick:
        return None
    price = tick.get("price")
    if price is None:
        return None
    return {
        "symbol": stock.get("symbol"),
        "exchange": stock.get("exchange"),
        "price": price,
        "change_pct": tick.get("percent_change") or tick.get("pChange") or 0,
        "high": tick.get("high_price_of_the_day") or tick.get("high"),
        "low": tick.get("low_price_of_the_day") or tick.get("low"),
        "volume": tick.get("volume_trade_for_the_day") or tick.get("volume"),
        "timestamp": tick.get("timestamp"),
    }


def _fetch_stock_quote(stock: dict, data_source: str) -> dict | None:
    symbol = stock.get("symbol")
    exchange = stock.get("exchange", "NSE")
    if not symbol:
        return None

    if data_source == "angel_one":
        client = _build_angel_client_from_session()
        if client:
            quote = client.get_quote(
                symbol=symbol,
                exchange=exchange,
                token=stock.get("token"),
                trading_symbol=stock.get("tradingsymbol") or symbol,
            )
            if quote:
                return quote

    return fetch_live_snapshot(symbol, exchange=exchange)


def _render_live_watchlist_body(selected_stocks: list[dict], data_source: str, limit: int = 12):
    """Render lightweight quote cards for selected symbols."""
    if not selected_stocks:
        return
    stream_message = ""
    if data_source == "angel_one":
        started, stream_message = stream_store.start(
            st.session_state.get("angel_jwt_token"),
            st.session_state.get("angel_feed_token"),
            selected_stocks[:limit],
        )
        if not started:
            stream_message = f"REST fallback: {stream_message}"
        elif stream_store.status == "streaming":
            stream_message = "Angel WebSocket streaming"
        else:
            stream_message = f"Angel WebSocket {stream_store.status}"

    st.subheader("Live Watchlist")
    st.caption(f"{stream_message or 'Quote refresh'} · {_now_label()}")

    unavailable = 0
    stocks = selected_stocks[:limit]
    for start in range(0, len(stocks), 4):
        cols = st.columns(min(4, len(stocks) - start))
        for col, stock in zip(cols, stocks[start:start + 4]):
            with col:
                quote = _quote_from_tick(stock, stream_store.latest(stock.get("token")))
                if not quote:
                    quote = _fetch_stock_quote(stock, data_source)
                if quote:
                    title = stock.get("symbol") or quote.get("symbol")
                    render_quote_tile(quote, title=title)
                else:
                    unavailable += 1
                    with st.container(border=True):
                        st.caption(stock.get("exchange", ""))
                        st.subheader(stock.get("symbol", "Unknown"))
                        st.metric("LTP", "Unavailable")

    if unavailable:
        st.caption(f"{unavailable} selected quote(s) are currently unavailable.")


def build_watchlist_quotes(selected_stocks: list[dict], data_source: str, limit: int = 12) -> dict[str, float]:
    price_lookup = {}
    for stock in selected_stocks[:limit]:
        quote = _quote_from_tick(stock, stream_store.latest(stock.get("token")))
        if not quote:
            quote = _fetch_stock_quote(stock, data_source)
        if quote:
            price = quote.get("price", quote.get("Price"))
            try:
                price_lookup[stock["symbol"]] = float(price)
            except (TypeError, ValueError):
                pass
    return price_lookup


def render_live_watchlist(
    selected_stocks: list[dict],
    data_source: str,
    enabled: bool,
    interval_seconds: int,
    limit: int = 12,
):
    """Render live quotes with fragment-level refresh to avoid full-page blinking."""
    if not selected_stocks:
        return

    if enabled and hasattr(st, "fragment"):
        live_fragment = st.fragment(run_every=f"{max(interval_seconds, 1)}s")(_render_live_watchlist_body)
        live_fragment(selected_stocks, data_source, limit)
        return

    _render_live_watchlist_body(selected_stocks, data_source, limit)
    if enabled:
        st.caption("Live quote streaming needs Streamlit fragments. Upgrade Streamlit for blink-free panel refresh.")


def _fetch_smart_data(symbol: str, exchange: str, period: str = "3mo") -> pd.DataFrame:
    """Fetches historical data handling NSE (.NS) and BSE (.BO) suffixes correctly."""
    try:
        index_symbols = {
            ("NSE", "NIFTY"): "^NSEI",
            ("NSE", "NIFTY 50"): "^NSEI",
            ("BSE", "SENSEX"): "^BSESN",
        }
        ticker = index_symbols.get((exchange, symbol.upper()))
        if not ticker:
            clean_symbol = symbol.replace("-EQ", "")
            suffix = ".BO" if exchange == "BSE" else ".NS"
            ticker = f"{clean_symbol}{suffix}"
        df = yf.Ticker(ticker).history(period=period)
        
        if df.empty:
            return pd.DataFrame()
            
        df.columns = [col.lower() for col in df.columns]
        df.reset_index(inplace=True)
        return df
    except Exception as e:
        st.warning(f"Failed to fetch data for {symbol} ({exchange}): {e}")
        return pd.DataFrame()


def _build_angel_client_from_session():
    """Create an AngelOneClient with the current session JWT, if available."""
    jwt = st.session_state.get("angel_jwt_token")
    if not jwt:
        return None

    from src.angel_client import AngelOneClient
    client = AngelOneClient()
    client.jwt_token = jwt
    client.feed_token = st.session_state.get("angel_feed_token") or jwt
    client.refresh_token = st.session_state.get("angel_refresh_token")
    return client


def _auto_connect_angel():
    """Login using .env credentials and store profile/JWT in session state."""
    if st.session_state.get("angel_jwt_token"):
        client = _build_angel_client_from_session()
        if client:
            profile = st.session_state.get("angel_profile") or client.get_profile()
            if profile:
                st.session_state["angel_profile"] = profile
                st.session_state.setdefault("angel_feed_token", client.feed_token or client.jwt_token)
                return True, "Already connected"
        st.session_state.pop("angel_jwt_token", None)
        st.session_state.pop("angel_profile", None)

    required = {
        "ANGEL_API_KEY": settings.angel_api_key,
        "ANGEL_CLIENT_CODE": settings.angel_client_code,
        "ANGEL_API_SECRET": settings.angel_api_secret,
        "ANGEL_TOTP_SECRET": settings.angel_totp_secret,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        return False, f"Missing .env values: {', '.join(missing)}"

    from src.angel_client import AngelOneClient
    client = AngelOneClient()
    if not client.login():
        return False, client.last_error or "Angel One login failed"

    st.session_state["angel_jwt_token"] = client.jwt_token
    st.session_state["angel_feed_token"] = client.feed_token
    st.session_state["angel_refresh_token"] = client.refresh_token
    profile = client.get_profile()
    if profile:
        st.session_state["angel_profile"] = profile

    angel = get_angel_master()
    angel.set_jwt_token(client.jwt_token)
    return True, "Connected"


def _fetch_index_quote(index: dict, data_source: str) -> dict | None:
    """Fetch Nifty/Sensex quote from Angel when connected, otherwise yfinance."""
    symbol = index["symbol"]
    exchange = index["exchange"]

    if data_source == "angel_one":
        client = _build_angel_client_from_session()
        if client:
            quote = client.get_quote(
                symbol=symbol,
                exchange=exchange,
                token=index.get("token"),
                trading_symbol=index.get("tradingsymbol", symbol),
            )
            if quote:
                return quote

    ticker = "^BSESN" if symbol == "SENSEX" else "^NSEI"
    hist = yf.Ticker(ticker).history(period="5d", interval="1d")
    if hist.empty:
        return None

    last = hist.iloc[-1]
    prev = hist.iloc[-2] if len(hist) > 1 else last
    change_pct = ((last["Close"] - prev["Close"]) / prev["Close"]) * 100 if prev["Close"] else 0
    return {
        "symbol": symbol,
        "exchange": exchange,
        "price": float(last["Close"]),
        "change_pct": float(change_pct),
    }


def render_market_indexes(data_source: str):
    """Render Nifty and Sensex cards."""
    indexes = [
        {"symbol": "NIFTY", "name": "Nifty 50", "exchange": "NSE", "token": "99926000", "tradingsymbol": "NIFTY"},
        {"symbol": "SENSEX", "name": "Sensex", "exchange": "BSE", "token": "99919000", "tradingsymbol": "SENSEX"},
    ]

    st.subheader("Market Pulse")
    st.caption(f"Updated {_now_label()}")
    cols = st.columns(len(indexes))
    for index in indexes:
        quote = _fetch_index_quote(index, data_source)
        with cols[indexes.index(index)]:
            if quote:
                quote["exchange"] = index["exchange"]
                render_quote_tile(quote, title=index["name"])
            else:
                with st.container(border=True):
                    st.caption(index["exchange"])
                    st.subheader(index["name"])
                    st.metric("LTP", "Unavailable")


def render_terminal_status(data_source: str, selected_stocks: list[dict], scan_scope: str):
    profile = st.session_state.get("angel_profile") or {}
    connected = bool(st.session_state.get("angel_jwt_token"))
    client_label = profile.get("clientcode") or profile.get("clientCode") or "Not connected"
    data_label = "Angel One SmartAPI" if data_source == "angel_one" else "Yahoo Finance"
    broker_label = "Connected" if connected else "Offline"
    stream_label = "Fragment live panel" if hasattr(st, "fragment") else "Manual refresh"

    cols = st.columns(5)
    cols[0].metric("Broker", broker_label, "Angel One")
    cols[1].metric("Client", client_label)
    cols[2].metric("Execution", "Paper", "No live orders")
    cols[3].metric("Data Feed", data_label, stream_label)
    cols[4].metric("Workspace", scan_scope.replace(" stocks", ""), f"{len(selected_stocks)} selected")


def render_angel_profile(profile: dict | None):
    """Render connected Angel One account profile in sidebar."""
    if not profile:
        return

    name = profile.get("name") or profile.get("clientname") or profile.get("clientName") or "Angel One"
    client_code = profile.get("clientcode") or profile.get("clientCode") or profile.get("client_code") or ""
    exchanges = profile.get("exchanges") or profile.get("exchange") or []
    products = profile.get("products") or []

    with st.sidebar.expander("Angel One Profile", expanded=True):
        st.caption("Connected account")
        st.write(f"**{name}**")
        if client_code:
            st.write(f"Client: `{client_code}`")
        if exchanges:
            st.write("Exchanges: " + ", ".join(map(str, exchanges)))
        if products:
            st.write("Products: " + ", ".join(map(str, products)))


def _send_telegram_messages(messages: list[str]) -> tuple[int, list[str]]:
    sent = 0
    failures = []
    for message in messages:
        result = send_telegram_alert(message)
        if result.ok:
            sent += 1
        else:
            failures.append(result.message)
    return sent, failures


def _format_screener_telegram_messages(df: pd.DataFrame, limit: int = 20) -> list[str]:
    if df.empty:
        return []

    messages = []
    for _, row in df.head(limit).iterrows():
        symbol = row.get("Symbol", "UNKNOWN")
        exchange = row.get("Exchange", "")
        price = row.get("Price", row.get("Price (₹)", "N/A"))
        rsi = row.get("RSI", "N/A")
        market_cap = row.get("Market Cap (Cr)", "N/A")
        messages.append(
            f"*Screener Match*: {symbol} ({exchange})\n"
            f"Price: ₹{price}\n"
            f"RSI: {rsi}\n"
            f"Market Cap: {market_cap} Cr"
        )
    if len(df) > limit:
        messages.append(f"{len(df) - limit} more screener matches not shown. Open ArthAI Terminal for full list.")
    return messages


def _render_telegram_feedback(sent: int, failures: list[str]):
    if sent and not failures:
        st.success(f"Sent {sent} Telegram notification(s).")
    elif sent and failures:
        st.warning(f"Sent {sent}, failed {len(failures)} Telegram notification(s).")
        with st.expander("Telegram failures"):
            st.write("\n".join(failures[:10]))
    else:
        failure_msg = failures[0] if failures else "No messages to send."
        st.error(f"Telegram not sent. {failure_msg}")


def render_market_side_panel(selected_stocks: list[dict], live_quotes: bool, refresh_interval: int):
    active = "On" if live_quotes else "Off"
    interval = f"{refresh_interval}s" if live_quotes else "Manual"
    selected = len(selected_stocks)
    primary = selected_stocks[0]["symbol"] if selected_stocks else "No symbol selected"

    with st.container(border=True):
        st.subheader("Desk Controls")
        st.metric("Live Panel", active, interval)
        st.metric("Watchlist", selected, primary)
        st.metric("Streaming", "Angel feed-ready", stream_store.status)


def _selected_universe(exchange_filter: list[str], max_stocks: int | None = None) -> list[dict]:
    angel = get_angel_master()
    universe = []
    for stock in angel.get_equities():
        exchange = stock.get("exch") or stock.get("exchange")
        if exchange not in exchange_filter:
            continue
        universe.append({
            "symbol": stock.get("symbol") or stock.get("tradingsymbol"),
            "name": stock.get("name"),
            "exchange": exchange,
            "token": stock.get("token"),
            "tradingsymbol": stock.get("tradingsymbol") or stock.get("symbol"),
            "instrumenttype": stock.get("instrumenttype", "EQ"),
        })

    if not universe:
        universe = [
            {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "exchange": "NSE"},
            {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "exchange": "NSE"},
            {"symbol": "INFY", "name": "Infosys Ltd", "exchange": "NSE"},
        ]

    return universe[:max_stocks] if max_stocks else universe


def run_custom_screener(query: str, universe: list[dict], sleep_seconds: float = 0.05) -> tuple[pd.DataFrame, list[str]]:
    import time

    conditions = parse_screener_query(query)
    rows = []
    errors = []

    progress = st.progress(0)
    status = st.empty()
    total = len(universe)

    for idx, stock in enumerate(universe, start=1):
        symbol = stock.get("symbol")
        status.caption(f"Scanning {idx:,}/{total:,}: {symbol}")
        progress.progress(idx / total)
        try:
            metrics = fetch_screener_metrics(stock)
            missing = []
            passed = True
            for condition in conditions:
                ok, missing_field = condition_passes(condition, metrics)
                if missing_field:
                    missing.append(missing_field)
                if not ok:
                    passed = False
                    break

            if passed:
                row = metrics_to_display_row(metrics)
                row["Missing Fields"] = ", ".join(sorted(set(missing)))
                rows.append(row)
        except Exception as e:
            if len(errors) < 20:
                errors.append(f"{symbol}: {e}")
        time.sleep(sleep_seconds)

    progress.empty()
    status.empty()
    return pd.DataFrame(rows), errors


@st.cache_data(ttl=86400, show_spinner=False)
def _cached_screener_metrics(symbol: str, name: str | None, exchange: str) -> dict:
    return fetch_screener_metrics({"symbol": symbol, "name": name, "exchange": exchange})


def run_cached_custom_screener(query: str, universe: list[dict]) -> tuple[pd.DataFrame, list[str]]:
    conditions = parse_screener_query(query)
    rows = []
    errors = []
    progress = st.progress(0)
    status = st.empty()
    total = len(universe)

    for idx, stock in enumerate(universe, start=1):
        symbol = stock.get("symbol")
        status.caption(f"Scanning {idx:,}/{total:,}: {symbol}")
        progress.progress(idx / total)
        try:
            metrics = _cached_screener_metrics(symbol, stock.get("name"), stock.get("exchange"))
            passed = True
            missing = []
            for condition in conditions:
                ok, missing_field = condition_passes(condition, metrics)
                if missing_field:
                    missing.append(missing_field)
                if not ok:
                    passed = False
                    break
            if passed:
                row = metrics_to_display_row(metrics)
                row["Missing Fields"] = ", ".join(sorted(set(missing)))
                rows.append(row)
        except Exception as e:
            if len(errors) < 30:
                errors.append(f"{symbol}: {e}")

    progress.empty()
    status.empty()
    return pd.DataFrame(rows), errors


# =============================================================================
# 🚀 Main Application
# =============================================================================

def main():
    # ─────────────────────────────────────────────────────────────────────
    # 🔐 Angel One Authentication (if configured)
    # ─────────────────────────────────────────────────────────────────────
    configured_source = getattr(settings, 'data_source', 'yfinance')
    data_source = st.sidebar.radio(
        "Data Source",
        options=["angel_one", "yfinance"],
        index=0 if st.session_state.get("data_source", configured_source) == "angel_one" else 1,
        format_func=lambda x: "Angel One SmartAPI" if x == "angel_one" else "Yahoo Finance",
        horizontal=True,
    )
    st.session_state["data_source"] = data_source
    
    if data_source == "angel_one":
        # Initialize Angel Master client for search
        angel = get_angel_master()

        connected, connection_message = _auto_connect_angel()
        if connected:
            st.sidebar.success("Angel One connected")
        else:
            st.sidebar.error("Angel One not connected")
            with st.sidebar.expander("Connection details", expanded=True):
                st.write(connection_message)
                st.caption("Using .env credentials only. Update .env, then restart Streamlit if values changed.")

        # Check if we have a JWT from a previous successful auto-login
        if not angel.jwt_token:
            # Try to get JWT from session state (set after login)
            jwt = st.session_state.get("angel_jwt_token")
            if jwt:
                angel.set_jwt_token(jwt)

        if angel.jwt_token and "angel_profile" not in st.session_state:
            client = _build_angel_client_from_session()
            if client:
                profile = client.get_profile()
                if profile:
                    st.session_state["angel_profile"] = profile

        render_angel_profile(st.session_state.get("angel_profile"))
    
    # Render enhanced sidebar (now with Angel One search if available)
    if "screener_query" not in st.session_state:
        st.session_state["screener_query"] = DEFAULT_SCREENER_QUERY
    (
        selected_stocks,
        rsi_range,
        run_scan,
        exchange_filter,
        scan_scope,
        screener_query,
        max_scan,
        live_quotes,
        refresh_interval,
    ) = render_sidebar()

    render_terminal_status(data_source, selected_stocks, scan_scope)

    widget_view = st.segmented_control(
        "Top widgets",
        options=["Market", "Watchlist", "Desk", "All", "Hide"],
        default=st.session_state.get("top_widget_view", "Market"),
        key="top_widget_view",
    )

    if widget_view == "Market":
        render_market_indexes(data_source)
    elif widget_view == "Watchlist":
        render_live_watchlist(selected_stocks, data_source, live_quotes, refresh_interval)
    elif widget_view == "Desk":
        render_market_side_panel(selected_stocks, live_quotes, refresh_interval)
    elif widget_view == "All":
        market_col, desk_col = st.columns([2.2, 1])
        with market_col:
            render_market_indexes(data_source)
            render_live_watchlist(selected_stocks, data_source, live_quotes, refresh_interval)
        with desk_col:
            render_market_side_panel(selected_stocks, live_quotes, refresh_interval)
    
    # Professional tab navigation
    tab_radar, tab_chart, tab_algo, tab_portfolio = st.tabs([
        "Screener Radar", 
        "Deep Dive & AI",
        "Algo Lab",
        "Paper Trading",
    ])
    
    # ─────────────────────────────────────────────────────────────────────
    # 📊 SCREENER RADAR TAB
    # ─────────────────────────────────────────────────────────────────────
    with tab_radar:
        if scan_scope == "Full universe":
            st.subheader("Full Universe Screener")
            st.caption("Free mode uses Angel One for master/quotes and cached Yahoo Finance data for fundamentals/technicals. First run is slow; repeated runs are faster from cache.")

            if run_scan:
                try:
                    universe = _selected_universe(
                        exchange_filter=[ex for ex in exchange_filter if ex in {"NSE", "BSE"}],
                        max_stocks=None if max_scan == 0 else max_scan,
                    )
                    with st.spinner(f"Scanning {len(universe):,} stocks..."):
                        screened_df, errors = run_cached_custom_screener(screener_query, universe)

                    if screened_df.empty:
                        render_status_indicator("info", "No stocks matched the screener conditions.")
                    else:
                        render_metric_card("Matches Found", str(len(screened_df)), "up", True)
                        st.dataframe(screened_df, width="stretch", height=520)
                        messages = _format_screener_telegram_messages(screened_df)
                        sent, failures = _send_telegram_messages(messages)
                        _render_telegram_feedback(sent, failures)

                        if st.button("Send Current Screener Results to Telegram", key="send_full_screener_telegram"):
                            sent, failures = _send_telegram_messages(messages)
                            _render_telegram_feedback(sent, failures)

                    if errors:
                        with st.expander(f"Skipped / unavailable data ({len(errors)} shown)"):
                            st.write("\n".join(errors))
                except ValueError as e:
                    render_status_indicator("error", f"Screener parse error: {e}")
                except Exception as e:
                    render_status_indicator("error", f"Screener failed: {e}")
            else:
                render_status_indicator("info", "Edit conditions in the sidebar, choose Full universe, then click Run Screener.")
            return

        if not selected_stocks:
            with st.container(border=True):
                st.subheader("Build a Watchlist")
                st.write("Search NSE/BSE instruments in the sidebar, select symbols, then run the screener.")
                c1, c2 = st.columns(2)
                c1.info("Try RELIANCE, TCS, INFY, NIFTY, or SENSEX.")
                c2.info("Tune RSI, exchange, and screener rules before scanning.")
            return
            
        if run_scan and selected_stocks:
            # Filter by exchange selection
            filtered_stocks = [
                stock for stock in selected_stocks
                if stock["exchange"] in exchange_filter
                or (stock.get("instrumenttype") == "INDEX" and "INDEX" in exchange_filter)
            ]
            
            if not filtered_stocks:
                render_status_indicator("warning", "No stocks match your Exchange filter criteria.")
                return
            
            with st.spinner(f"Scanning {len(filtered_stocks)} assets..."):
                progress_bar = st.progress(0)
                results = []
                
                for idx, stock in enumerate(filtered_stocks):
                    progress_bar.progress((idx + 1) / len(filtered_stocks))
                    
                    symbol = stock["symbol"]
                    exchange = stock["exchange"]
                    token = stock.get("token")
                    trading_symbol = stock.get("tradingsymbol") or symbol
                    instrument_type = stock.get("instrumenttype", "EQ")
                    
                    # Fetch and process data
                    hist_df = _fetch_smart_data(symbol, exchange)
                    if hist_df.empty:
                        continue
                    
                    hist_df = calculate_technical_indicators(hist_df)
                    latest_row = hist_df.iloc[-1]
                    
                    # Get live price (try Angel One first if configured)
                    live_price = latest_row['close']
                    if data_source == "angel_one":
                        try:
                            from src.angel_client import AngelOneClient
                            client = AngelOneClient()
                            client.jwt_token = st.session_state.get("angel_jwt_token")
                            if client.jwt_token:
                                quote = client.get_quote(
                                    symbol=symbol,
                                    exchange=exchange,
                                    token=token,
                                    trading_symbol=trading_symbol,
                                )
                                if quote:
                                    live_price = quote["price"]
                        except:
                            pass  # Fallback to yfinance price
                    
                    # Build result row with formatted alerts
                    alerts = check_screener_rules(latest_row)
                    alert_badges = " ".join([
                        render_alert_badge(alert, alert.split()[0].lower().rstrip(':'))
                        for alert in alerts if alert
                    ])
                    
                    price_formatted = f"{live_price:,.2f}"
                    rsi_formatted = f"{latest_row.get('rsi_14', 50):.1f}"
                    ema_formatted = f"{latest_row.get('ema_20', 0):.1f}"
                    
                    row_data = {
                        "Symbol": symbol,
                        "Exchange": exchange,
                        "Type": instrument_type,
                        "Price (₹)": price_formatted,
                        "Change_Pct": "N/A",
                        "RSI": rsi_formatted,
                        "EMA20": ema_formatted,
                        "Alerts": alert_badges,
                        "_raw_alerts": ", ".join(alerts),
                        "_price_numeric": live_price,
                        "_rsi_numeric": latest_row.get('rsi_14', 50)
                    }
                    results.append(row_data)
                
                progress_bar.empty()
            
            if results:
                df = pd.DataFrame(results)
                
                # Apply RSI filter
                filtered_df = df[
                    (df["_rsi_numeric"] >= rsi_range[0]) & 
                    (df["_rsi_numeric"] <= rsi_range[1])
                ].copy()
                
                if not filtered_df.empty:
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        render_metric_card("Stocks Scanned", str(len(results)))
                    with col2:
                        render_metric_card("Matches Found", str(len(filtered_df)), "up", True)
                    with col3:
                        avg_rsi = filtered_df["_rsi_numeric"].mean()
                        avg_rsi_str = f"{avg_rsi:.1f}"
                        render_metric_card("Avg RSI", avg_rsi_str)
                    with col4:
                        alert_count = filtered_df[filtered_df["_raw_alerts"] != ""].shape[0]
                        render_metric_card("Alerts", str(alert_count), "up" if alert_count > 0 else None, alert_count > 0)
                    
                    st.divider()
                    
                    # Display professional data grid
                    display_df = filtered_df.drop(columns=["_raw_alerts", "_price_numeric", "_rsi_numeric"])
                    render_data_grid(display_df)

                    selected_messages = []
                    for _, row in filtered_df.iterrows():
                        price_clean = row['Price (₹)'].replace(',', '')
                        alert_text = row['_raw_alerts'] or "Matched selected-stock screener filters"
                        selected_messages.append(
                            f"*{row['Symbol']} ({row['Exchange']})* @ ₹{price_clean}\n{alert_text}"
                        )

                    sent, failures = _send_telegram_messages(selected_messages)
                    _render_telegram_feedback(sent, failures)

                    if st.button("Send Current Results to Telegram", key="send_selected_screener_telegram"):
                        sent, failures = _send_telegram_messages(selected_messages)
                        _render_telegram_feedback(sent, failures)
                    
                    # Telegram alerts for triggered stocks
                    alert_stocks = filtered_df[filtered_df["_raw_alerts"] != ""]
                    if not alert_stocks.empty:
                        render_status_indicator("success", f"{len(alert_stocks)} alert(s) triggered.")
                else:
                    rsi_msg = f"No stocks matched RSI range {rsi_range[0]}-{rsi_range[1]}. Try adjusting filters."
                    render_status_indicator("info", rsi_msg)
            else:
                render_status_indicator("error", "No valid data returned for selected tickers. Check symbols or try again.")
    
    # ─────────────────────────────────────────────────────────────────────
    # 📈 DEEP DIVE & AI TAB (Multi-Chart Panel)
    # ─────────────────────────────────────────────────────────────────────
    with tab_chart:
        if "active_charts" not in st.session_state:
            st.session_state["active_charts"] = selected_stocks[:1] if selected_stocks else []

        if not selected_stocks:
            with st.container(border=True):
                st.subheader("Select Stocks First")
                st.write("Use the sidebar stock finder to add equities to your Active Watchlist.")
            return

        # Double-check constraints
        st.session_state["active_charts"] = [
            c for c in st.session_state["active_charts"]
            if any(item["symbol"] == c["symbol"] and item["exchange"] == c["exchange"] for item in selected_stocks)
        ]
        if not st.session_state["active_charts"] and selected_stocks:
            st.session_state["active_charts"] = [selected_stocks[0]]

        # 📊 Grid & Window Panel Settings Controller
        st.markdown("### 📊 Interactive Multi-Chart Panel")
        with st.expander("🛠️ Panel View & Windows Controller (Manage Grid Layout)", expanded=False):
            st.caption("Display up to 4 independent charts simultaneously in a dynamic grid layout.")
            
            c_add, c_actions = st.columns([2, 1])
            with c_add:
                inactive_stocks = [
                    s for s in selected_stocks
                    if not any(ac["symbol"] == s["symbol"] and ac["exchange"] == s["exchange"] for ac in st.session_state["active_charts"])
                ]
                if inactive_stocks:
                    add_opts = [f"{s['symbol']} ({s['exchange']})" for s in inactive_stocks]
                    to_add = st.selectbox("Select stock to add to panel", options=add_opts, key="chart_add_picker")
                    if st.button("➕ Add Chart Window", type="primary", use_container_width=True):
                        if len(st.session_state["active_charts"]) < 4:
                            parts = to_add.split(" (")
                            add_sym = parts[0]
                            add_exch = parts[1].rstrip(")")
                            stock_to_add = next(s for s in selected_stocks if s["symbol"] == add_sym and s["exchange"] == add_exch)
                            st.session_state["active_charts"].append(stock_to_add)
                            st.toast(f"Added {add_sym} to Chart Panel!")
                            st.rerun()
                        else:
                            st.error("Max 4 charts can be displayed simultaneously.")
                else:
                    st.info("All watchlist stocks are currently active on the panel.")
            with c_actions:
                if st.button("🔄 Reset Panel (Show 1 Chart)", use_container_width=True):
                    st.session_state["active_charts"] = [selected_stocks[0]]
                    st.rerun()
                if st.button("❌ Clear All Charts", use_container_width=True):
                    st.session_state["active_charts"] = []
                    st.rerun()

        if not st.session_state["active_charts"]:
            st.info("No active charts on screen. Manage windows above or add a stock.")
            return

        # ─────────────────────────────────────────────────────────────────────
        # 🎨 Chart Grid Layout Renderer (1x1, 1x2, or 2x2 Grid)
        # ─────────────────────────────────────────────────────────────────────
        active_panels = st.session_state["active_charts"][:4]
        n_charts = len(active_panels)

        # Build grid cells
        grid_cells = []
        if n_charts == 1:
            grid_cells = [st.container(border=True)]
        elif n_charts == 2:
            cols = st.columns(2)
            grid_cells = [cols[0], cols[1]]
        elif n_charts == 3:
            cols_r1 = st.columns(2)
            cols_r2 = st.columns([1, 1])
            grid_cells = [cols_r1[0], cols_r1[1], cols_r2[0]]
        else: # 4 charts
            cols_r1 = st.columns(2)
            cols_r2 = st.columns(2)
            grid_cells = [cols_r1[0], cols_r1[1], cols_r2[0], cols_r2[1]]

        # Render each panel card
        for idx, target in enumerate(active_panels):
            with grid_cells[idx]:
                # Top header bar inside panel card
                col_lbl, col_rem = st.columns([4, 1])
                col_lbl.markdown(f"##### 📈 **{target['symbol']}** · {target['exchange']}")
                
                # Close button
                if col_rem.button("❌", key=f"close_card_{idx}_{target['symbol']}", help="Close this chart card"):
                    st.session_state["active_charts"].pop(idx)
                    st.toast(f"Closed {target['symbol']} chart panel.")
                    st.rerun()

                # Card configurations
                c1, c2, c3 = st.columns(3)
                with c1:
                    # Switch stock option
                    opts = [f"{s['symbol']} ({s['exchange']})" for s in selected_stocks]
                    def_idx = 0
                    for o_idx, o in enumerate(opts):
                        if o.startswith(target['symbol'] + " ("):
                            def_idx = o_idx
                            break
                    switched = st.selectbox(
                        "Stock", 
                        options=opts, 
                        index=def_idx, 
                        key=f"switch_stock_{idx}_{target['symbol']}"
                    )
                    s_parts = switched.split(" (")
                    s_sym = s_parts[0]
                    s_exch = s_parts[1].rstrip(")")
                    if s_sym != target['symbol'] or s_exch != target['exchange']:
                        new_stock = next(s for s in selected_stocks if s["symbol"] == s_sym and s["exchange"] == s_exch)
                        st.session_state["active_charts"][idx] = new_stock
                        st.rerun()
                with c2:
                    period = st.selectbox("Period", ["3mo", "6mo", "1y", "2y", "5y"], index=1, key=f"period_{idx}_{target['symbol']}")
                with c3:
                    interval = st.selectbox("Interval", ["1d", "1wk", "1mo"], index=0, key=f"interval_{idx}_{target['symbol']}")

                # Overlay / Indicator Toggles Popover
                with st.popover("⚙️ Indicators & Overlays", use_container_width=True):
                    overlays = st.multiselect(
                        "Chart Overlays",
                        ["EMA 20", "SMA 50", "SMA 200", "Bollinger Bands", "VWAP"],
                        default=["EMA 20", "SMA 50"],
                        key=f"overlays_picker_{idx}_{target['symbol']}"
                    )
                    lower = st.multiselect(
                        "Lower Indicators",
                        ["Volume", "RSI", "MACD"],
                        default=["Volume", "RSI"],
                        key=f"lower_picker_{idx}_{target['symbol']}"
                    )

                # Render dynamic chart
                if target.get("instrumenttype") == "INDEX":
                    yahoo_ticker = "^BSESN" if target["symbol"] == "SENSEX" else "^NSEI"
                else:
                    clean_symbol = target['symbol'].replace("-EQ", "")
                    yahoo_ticker = f"{clean_symbol}{'.BO' if target['exchange'] == 'BSE' else '.NS'}"
                
                try:
                    df = render_chart(
                        yahoo_ticker,
                        period=period,
                        interval=interval,
                        overlays=overlays,
                        lower_indicators=lower,
                        dark_mode=True,
                    )
                except Exception as e:
                    st.error(f"Failed to render chart: {e}")
                    df = pd.DataFrame()

                # Card metrics footer
                if not df.empty and 'close' in df.columns:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest
                    change = ((latest['close'] - prev['close']) / prev['close']) * 100
                    rsi_val = latest.get('rsi_14', 50)
                    
                    st.markdown("---")
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    col_m1.metric("LTP", f"₹{latest['close']:,.2f}")
                    col_m2.metric("Change", f"{change:+.2f}%", delta=f"{change:+.2f}%")
                    col_m3.metric("RSI(14)", f"{rsi_val:.1f}")
                    col_m4.metric("Volume", f"{latest.get('volume', 0):,}")

                    # Embedded Local AI Analysis Popover
                    with st.popover("🤖 Run Local AI Desk", use_container_width=True):
                        st.markdown(f"#### Local AI Trade Plan for {target['symbol']}")
                        focus_area = st.selectbox(
                            "Focus",
                            options=["momentum", "support_resistance", "breakout", "reversal", "swing_trade"],
                            format_func=lambda x: x.replace("_", " ").title(),
                            key=f"ai_focus_{idx}_{target['symbol']}"
                        )
                        if st.button(
                            "🧠 Consult Local AI Model",
                            key=f"run_ai_btn_{idx}_{target['symbol']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            with st.spinner("Analyzing with local LLM..."):
                                ai_response = generate_ai_trade_plan(
                                    ticker=target['symbol'],
                                    tech_df=df,
                                    focus=focus_area,
                                )
                            st.markdown(ai_response)
                            if st.button(
                                "📤 Send to Telegram",
                                key=f"tg_btn_{idx}_{target['symbol']}",
                                use_container_width=True,
                            ):
                                msg = f"*AI Trade Desk: {target['symbol']}*\n{ai_response[:1000]}"
                                result = send_telegram_alert(msg)
                                st.success("Sent!") if result.ok else st.error(result.message)

    # ─────────────────────────────────────────────────────────────────────
    # ⚙️ ALGO LAB TAB
    # ─────────────────────────────────────────────────────────────────────
    with tab_algo:
        render_algo_lab()
    
    # ─────────────────────────────────────────────────────────────────────
    # 🧾 PAPER TRADING TAB
    # ─────────────────────────────────────────────────────────────────────
    with tab_portfolio:
        price_lookup = build_watchlist_quotes(selected_stocks, data_source, limit=25)
        for stock in selected_stocks:
            if stock["symbol"] in price_lookup:
                continue
            try:
                hist = _fetch_smart_data(stock["symbol"], stock["exchange"], period="5d")
                if not hist.empty:
                    price_lookup[stock["symbol"]] = float(hist.iloc[-1]["close"])
            except Exception:
                pass
        render_paper_trading(selected_stocks, price_lookup=price_lookup)
    
    # ─────────────────────────────────────────────────────────────────────
    # 🦶 Professional Footer
    # ─────────────────────────────────────────────────────────────────────
    st.divider()
    st.caption("ArthAI Terminal v1.0 · NSE/BSE data via Angel One/yfinance · AI via local Ollama · Telegram alerts")


# =============================================================================
# 🚀 Application Entry Point
# =============================================================================

if __name__ == "__main__":
    main()
