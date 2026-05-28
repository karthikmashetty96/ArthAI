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
    st.sidebar.header("🕹️ Terminal Controls")
    st.sidebar.subheader("⚡ Live Price Engine")

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
    # 🔍 Stock Search with Angel One + Public Fallback
    # ─────────────────────────────────────────────────────────────────────
    st.sidebar.subheader("🔍 Stock Finder")
    search_query = st.sidebar.text_input(
        "Search Symbol or Name",
        placeholder="Type RELIANCE, TCS, bank, 500325...",
        key="stock_search",
        help="Search across NSE/BSE. Local fallback is active if the broker master is offline."
    )
    
    # Initialize Angel Master client
    angel = get_angel_master()
    if not angel.jwt_token:
        jwt = st.session_state.get("angel_jwt_token")
        if jwt:
            angel.set_jwt_token(jwt)
            
    # Load counts for statistics
    all_equities_count = 0
    all_indexes_count = 0
    try:
        all_equities_count = len(angel.get_equities())
        all_indexes_count = len(angel.get_indexes())
    except:
        pass
        
    search_results = []
    if "selected_stocks" not in st.session_state:
        st.session_state["selected_stocks"] = []

    if search_query and len(search_query.strip()) >= 2:
        query = search_query.strip()
        
        # 1. Try Broker Search
        try:
            search_results = angel.search(query, limit=20)
        except Exception:
            search_results = []
            
        # 2. ALSO merge with public search fallback to cover "All NSE and BSE stocks"!
        try:
            from src.stock_universe import search_stocks as public_search
            public_results = public_search(query, limit=20)
            for ps in public_results:
                symbol = ps["symbol"]
                exchange = ps["exchange"]
                name = ps["name"]
                
                # Check if we already have it in search_results
                already_exists = any(
                    (s.get("symbol") or s.get("tradingsymbol") or "").upper() == symbol.upper() 
                    and (s.get("exch") or s.get("exchange") or "").upper() == exchange.upper()
                    for s in search_results
                )
                if not already_exists:
                    search_results.append({
                        "symbol": symbol,
                        "name": name,
                        "exch": exchange,
                        "exchange": exchange,
                        "token": ps.get("token", ""),
                        "tradingsymbol": symbol,
                        "instrumenttype": "EQ"
                    })
        except Exception as e:
            pass

        # Display Search Results with + Add Buttons
        if search_results:
            st.sidebar.markdown("**Search Results**")
            # Show top 5 for neat styling
            for s in search_results[:5]:
                sym = s.get("symbol") or s.get("tradingsymbol")
                exch = s.get("exch") or s.get("exchange") or "NSE"
                name_trimmed = s.get("name", "")[:24]
                
                col_info, col_add = st.sidebar.columns([3.5, 1])
                col_info.markdown(f"**{sym}** ({exch})<br><span style='font-size:0.75rem;color:#94a3b8;'>{name_trimmed}</span>", unsafe_allow_html=True)
                
                # Add button
                if col_add.button("➕", key=f"add_{sym}_{exch}_{s.get('token')}"):
                    # Normalize stock dict
                    stock_item = {
                        "symbol": sym,
                        "name": s.get("name"),
                        "exchange": exch,
                        "token": s.get("token"),
                        "tradingsymbol": s.get("tradingsymbol") or sym,
                        "instrumenttype": s.get("instrumenttype", "EQ"),
                    }
                    # Add to session state list if not already present
                    exists = any(
                        item["symbol"] == sym and item["exchange"] == exch
                        for item in st.session_state["selected_stocks"]
                    )
                    if not exists:
                        st.session_state["selected_stocks"].append(stock_item)
                        st.toast(f"Added {sym} ({exch}) to Watchlist!")
                        st.rerun()
                    else:
                        st.toast(f"{sym} is already in Watchlist.")
        else:
            st.sidebar.caption("No matching equities found.")
            
    # ─────────────────────────────────────────────────────────────────────
    # 📋 Active Watchlist Widget with "-" Buttons
    # ─────────────────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Active Watchlist")
    
    if st.session_state["selected_stocks"]:
        for idx, item in enumerate(st.session_state["selected_stocks"]):
            col_lbl, col_rem = st.sidebar.columns([3.5, 1])
            lbl_text = f"**{item['symbol']}** ({item['exchange']})"
            col_lbl.markdown(f"<div style='padding-top:4px;'>{lbl_text}</div>", unsafe_allow_html=True)
            
            # Remove button
            if col_rem.button("❌", key=f"rem_{item['symbol']}_{item['exchange']}_{idx}"):
                st.session_state["selected_stocks"].pop(idx)
                st.toast(f"Removed {item['symbol']}!")
                st.rerun()
    else:
        # Prepopulate with defaults if totally empty to help initial load
        st.session_state["selected_stocks"] = [
            {"symbol": "NIFTY", "name": "Nifty 50", "exchange": "NSE", "token": "99926000", "tradingsymbol": "NIFTY", "instrumenttype": "INDEX"},
            {"symbol": "SENSEX", "name": "Sensex", "exchange": "BSE", "token": "99919000", "tradingsymbol": "SENSEX", "instrumenttype": "INDEX"},
            {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "exchange": "NSE"}
        ]
        st.rerun()
        
    selected_stocks = st.session_state["selected_stocks"]
    
    # ─────────────────────────────────────────────────────────────────────
    # 📊 Filter Rules
    # ─────────────────────────────────────────────────────────────────────
    st.sidebar.subheader("🎯 Scan Radar Criteria")

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
    # 🔄 Cache Refresh & Stats (Expander)
    # ─────────────────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    
    with st.sidebar.expander("📊 Database & Statistics", expanded=False):
        if st.button("Refresh Master List", type="secondary", use_container_width=True):
            with st.sidebar.spinner("Fetching latest stock list..."):
                angel.fetch_master_list(force_refresh=True)
            st.sidebar.success("Master list refreshed.")
            st.rerun()
        
        # Stats
        col1, col2 = st.columns(2)
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
