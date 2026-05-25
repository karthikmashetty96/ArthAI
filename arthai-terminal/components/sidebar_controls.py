# components/sidebar_controls.py - Angel One Enhanced Version
import streamlit as st
from src.angel_master import get_angel_master

# Fallback stocks if Angel One unavailable
FALLBACK_STOCKS = [
    {"symbol": "NIFTY", "name": "Nifty 50", "exchange": "NSE", "token": "99926000", "tradingsymbol": "NIFTY", "instrumenttype": "INDEX"},
    {"symbol": "SENSEX", "name": "Sensex", "exchange": "BSE", "token": "99919000", "tradingsymbol": "SENSEX", "instrumenttype": "INDEX"},
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "exchange": "NSE"},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "exchange": "NSE"},
    {"symbol": "INFY", "name": "Infosys Ltd", "exchange": "NSE"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "exchange": "NSE"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "exchange": "NSE"},
    {"symbol": "SBIN", "name": "State Bank of India", "exchange": "NSE"},
    {"symbol": "500325", "name": "Reliance Industries Ltd", "exchange": "BSE"},
    {"symbol": "532540", "name": "Tata Consultancy Services Ltd", "exchange": "BSE"},
]

def _instrument_label(inst: dict) -> str:
    symbol = inst.get("symbol") or inst.get("tradingsymbol") or ""
    name = inst.get("name") or symbol
    exchange = inst.get("exch") or inst.get("exchange") or ""
    token = inst.get("token", "")
    instrument_type = inst.get("instrumenttype") or "EQ"
    return f"{symbol} - {name} ({exchange}) [{instrument_type}|{token}]"


def _fallback_label(stock: dict) -> str:
    return _instrument_label({
        "symbol": stock["symbol"],
        "name": stock["name"],
        "exch": stock["exchange"],
        "token": stock.get("token", ""),
        "instrumenttype": stock.get("instrumenttype", "EQ"),
        "tradingsymbol": stock.get("tradingsymbol", stock["symbol"]),
    })


def render_sidebar():
    st.sidebar.header("Terminal Controls")
    st.sidebar.subheader("Live Quotes")

    live_quotes = st.sidebar.toggle(
        "Live market panel",
        value=st.session_state.get("live_quotes", True),
        help="Updates only the quote panel using Streamlit fragments when supported."
    )
    st.session_state["live_quotes"] = live_quotes

    refresh_interval = st.sidebar.slider(
        "Quote interval",
        min_value=1,
        max_value=30,
        value=int(st.session_state.get("refresh_interval", 2)),
        step=1,
        format="%d sec",
        disabled=not live_quotes,
        help="Use 1 second for Nifty/index tracking if your API rate limits allow it."
    )
    st.session_state["refresh_interval"] = refresh_interval
    
    # ─────────────────────────────────────────────────────────────────────
    # 🔍 Stock Search with Angel One Master List
    # ─────────────────────────────────────────────────────────────────────
    
    search_query = st.sidebar.text_input(
        "Search Stocks",
        placeholder="Type symbol or name... e.g., RELIANCE, bank, 500325",
        key="stock_search",
        help="Search by:\n• Symbol: RELIANCE, TCS\n• Name: reliance, bank, auto\n• BSE code: 500325"
    )
    
    # Initialize Angel Master client
    angel = get_angel_master()
    
    # Check if we have JWT token (set by main app after login)
    if not angel.jwt_token:
        # Try to get from session state (set by app.py after auth)
        jwt = st.session_state.get("angel_jwt_token")
        if jwt:
            angel.set_jwt_token(jwt)
    
    # Build stock options list
    stock_options = []
    search_results = []
    label_to_stock = {}
    all_equities_count = 0
    all_indexes_count = 0

    if search_query and len(search_query.strip()) >= 2:
        # Search using Angel One master list
        query = search_query.strip()
        search_results = angel.search(query, limit=250)
        
        if search_results:
            for s in search_results:
                label = _instrument_label(s)
                stock_options.append(label)
                label_to_stock[label] = s
        else:
            # No results - show helpful message + fallback
            st.sidebar.info(f"No stocks found for '{query}'. Try RELIANCE, TCS, bank, or 500325.")
            for s in FALLBACK_STOCKS:
                label = _fallback_label(s)
                stock_options.append(label)
                label_to_stock[label] = s
    
    else:
        # No search: show indexes first, then full NSE/BSE equity universe.
        try:
            indexes = angel.get_indexes()
            equities = angel.get_equities()
            all_indexes_count = len(indexes)
            all_equities_count = len(equities)
            instruments = indexes + equities

            if instruments:
                for s in instruments:
                    label = _instrument_label(s)
                    stock_options.append(label)
                    label_to_stock[label] = s
            else:
                for s in FALLBACK_STOCKS:
                    label = _fallback_label(s)
                    stock_options.append(label)
                    label_to_stock[label] = s
        except Exception as e:
            st.sidebar.warning(f"Using fallback list: {str(e)[:40]}...")
            for s in FALLBACK_STOCKS:
                label = _fallback_label(s)
                stock_options.append(label)
                label_to_stock[label] = s
    
    # ─────────────────────────────────────────────────────────────────────
    # 📋 Multi-select Stock Picker
    # ─────────────────────────────────────────────────────────────────────
    
    selected_labels = st.sidebar.multiselect(
        "Select Stocks",
        options=stock_options,
        placeholder="Search and select stocks...",
        default=[],
        help="Type to filter. Hold Ctrl/Cmd to select multiple."
    )
    
    # Parse selected labels to extract symbol + exchange
    selected_stocks = []
    for label in selected_labels:
        inst = label_to_stock.get(label)
        if inst:
            exchange = inst.get("exch") or inst.get("exchange")
            selected_stocks.append({
                "symbol": inst.get("symbol") or inst.get("tradingsymbol"),
                "name": inst.get("name"),
                "exchange": exchange,
                "token": inst.get("token"),
                "tradingsymbol": inst.get("tradingsymbol") or inst.get("symbol"),
                "instrumenttype": inst.get("instrumenttype", "EQ"),
            })
            continue

        # Fallback parse for restored Streamlit selections.
        try:
            parts = label.split(" - ")
            symbol = parts[0].strip()
            exchange = label.split("(")[-1].strip(")")
            selected_stocks.append({"symbol": symbol, "exchange": exchange})
        except:
            continue
    
    # ─────────────────────────────────────────────────────────────────────
    # 📊 Filter Rules
    # ─────────────────────────────────────────────────────────────────────
    st.sidebar.subheader("Filter Rules")

    scan_scope = st.sidebar.radio(
        "Scan Scope",
        options=["Selected stocks", "Full universe"],
        horizontal=True,
        help="Use search selection for deep dives, or scan all NSE/BSE stocks from Angel master."
    )

    screener_query = st.sidebar.text_area(
        "Screener Conditions",
        value=st.session_state.get("screener_query", ""),
        height=180,
        placeholder="Market Capitalization > 500 AND\nCurrent price > DMA 50 AND\nRSI > 55",
        help="Use Screener.in-style conditions joined with AND."
    )
    st.session_state["screener_query"] = screener_query

    max_scan = st.sidebar.number_input(
        "Max stocks to scan",
        min_value=0,
        max_value=10000,
        value=250,
        step=50,
        help="0 scans every available stock. A smaller number is faster while testing."
    )
    
    rsi_range = st.sidebar.slider(
        "RSI Range", 0, 100, (30, 70), step=5,
        help="<30 = Oversold (buy signal) | >70 = Overbought (sell signal)"
    )
    
    exchange_filter = st.sidebar.multiselect(
        "Exchange",
        options=["NSE", "BSE", "INDEX"],
        default=["NSE", "BSE", "INDEX"]
    )
    
    # ─────────────────────────────────────────────────────────────────────
    # ⚡ Run Button
    # ─────────────────────────────────────────────────────────────────────
    run_scan = st.sidebar.button(
        "Run Screener", 
        type="primary", 
        use_container_width=True
    )
    
    # ─────────────────────────────────────────────────────────────────────
    # 🔄 Cache Refresh & Stats
    # ─────────────────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    
    if st.sidebar.button("Refresh Master List", type="secondary", use_container_width=True):
        with st.sidebar.spinner("Fetching latest stock list..."):
            angel.fetch_master_list(force_refresh=True)
        st.sidebar.success("Master list refreshed.")
        st.rerun()
    
    # Stats
    col1, col2 = st.sidebar.columns(2)
    with col1:
        total = all_equities_count + all_indexes_count
        if total == 0:
            total = len(angel.get_equities()) + len(angel.get_indexes()) if angel._master_list else len(FALLBACK_STOCKS)
        st.metric("Available", f"{total:,}")
    with col2:
        st.metric("Selected", len(selected_stocks))
    
    # Tips
    st.sidebar.caption(
        "Search tips: NSE symbols like RELIANCE, TCS, INFY; "
        "BSE codes like 500325; or names/sectors like bank, auto, pharma, IT."
    )
    
    return (
        selected_stocks,
        rsi_range,
        run_scan,
        exchange_filter,
        scan_scope,
        screener_query,
        int(max_scan),
        live_quotes,
        int(refresh_interval),
    )
