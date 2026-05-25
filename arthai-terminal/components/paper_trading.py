import pandas as pd
import streamlit as st


INITIAL_CASH = 1_000_000.0
DEFAULT_RISK_PCT = 1.0


def _state():
    if "paper_cash" not in st.session_state:
        st.session_state.paper_cash = INITIAL_CASH
    if "paper_positions" not in st.session_state:
        st.session_state.paper_positions = {}
    if "paper_orders" not in st.session_state:
        st.session_state.paper_orders = []
    if "paper_realized_pnl" not in st.session_state:
        st.session_state.paper_realized_pnl = 0.0
    if "paper_equity_curve" not in st.session_state:
        st.session_state.paper_equity_curve = []


def _portfolio_value(prices: dict[str, float]) -> float:
    value = st.session_state.paper_cash
    for symbol, pos in st.session_state.paper_positions.items():
        value += pos["qty"] * prices.get(symbol, pos["avg_price"])
    return value


def _positions_frame(prices: dict[str, float]) -> pd.DataFrame:
    rows = []
    for symbol, pos in st.session_state.paper_positions.items():
        last_price = prices.get(symbol, pos["avg_price"])
        pnl = (last_price - pos["avg_price"]) * pos["qty"]
        rows.append({
            "Symbol": symbol,
            "Qty": pos["qty"],
            "Avg Price": pos["avg_price"],
            "Last Price": last_price,
            "Market Value": last_price * pos["qty"],
            "Unrealized P&L": pnl,
            "Unrealized %": (pnl / (pos["avg_price"] * pos["qty"])) * 100 if pos["qty"] else 0,
            "Stop Loss": pos.get("stop_loss"),
            "Target": pos.get("target"),
            "Strategy": pos.get("strategy", "Manual"),
        })
    return pd.DataFrame(rows)


def _record_equity(prices: dict[str, float]):
    value = _portfolio_value(prices)
    curve = st.session_state.paper_equity_curve
    if not curve or curve[-1]["Value"] != value:
        curve.append({"Step": len(curve) + 1, "Value": value})


def _buy(symbol: str, qty: int, price: float, strategy: str, stop_loss: float | None, target: float | None) -> tuple[bool, str]:
    notional = price * qty
    if notional > st.session_state.paper_cash:
        return False, "Not enough paper cash."

    positions = st.session_state.paper_positions
    pos = positions.get(symbol, {"qty": 0, "avg_price": 0.0, "strategy": strategy})
    new_qty = pos["qty"] + qty
    avg_price = ((pos["qty"] * pos["avg_price"]) + notional) / new_qty
    positions[symbol] = {
        "qty": new_qty,
        "avg_price": avg_price,
        "strategy": strategy,
        "stop_loss": stop_loss,
        "target": target,
    }
    st.session_state.paper_cash -= notional
    st.session_state.paper_orders.append({
        "Symbol": symbol,
        "Side": "BUY",
        "Qty": qty,
        "Price": price,
        "Value": notional,
        "Strategy": strategy,
    })
    return True, "Paper buy filled."


def _sell(symbol: str, qty: int, price: float, reason: str = "Manual") -> tuple[bool, str]:
    positions = st.session_state.paper_positions
    pos = positions.get(symbol)
    if not pos or pos["qty"] < qty:
        return False, "Not enough paper quantity to sell."

    notional = price * qty
    realized = (price - pos["avg_price"]) * qty
    pos["qty"] -= qty
    st.session_state.paper_cash += notional
    st.session_state.paper_realized_pnl += realized
    if pos["qty"] == 0:
        del positions[symbol]

    st.session_state.paper_orders.append({
        "Symbol": symbol,
        "Side": "SELL",
        "Qty": qty,
        "Price": price,
        "Value": notional,
        "Realized P&L": realized,
        "Reason": reason,
    })
    return True, "Paper sell filled."


def _risk_quantity(entry: float, stop_loss: float, equity: float, risk_pct: float) -> int:
    risk_per_share = max(entry - stop_loss, 0)
    if risk_per_share <= 0:
        return 1
    risk_amount = equity * (risk_pct / 100)
    return max(int(risk_amount // risk_per_share), 1)


def _fmt_money(value: float | None) -> str:
    if value is None:
        return "-"
    return f"₹{float(value):,.2f}"


def _positions_table(df: pd.DataFrame):
    st.dataframe(
        df,
        width="stretch",
        height=340,
        hide_index=True,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol", width="small"),
            "Qty": st.column_config.NumberColumn("Qty", width="small"),
            "Avg Price": st.column_config.NumberColumn("Avg", format="₹%.2f"),
            "Last Price": st.column_config.NumberColumn("LTP", format="₹%.2f"),
            "Market Value": st.column_config.NumberColumn("Value", format="₹%.2f"),
            "Unrealized P&L": st.column_config.NumberColumn("P&L", format="₹%.2f"),
            "Unrealized %": st.column_config.NumberColumn("P&L %", format="%.2f%%"),
            "Stop Loss": st.column_config.NumberColumn("SL", format="₹%.2f"),
            "Target": st.column_config.NumberColumn("Target", format="₹%.2f"),
        },
    )


def render_paper_trading(selected_stocks: list[dict], price_lookup: dict[str, float] | None = None):
    _state()
    price_lookup = price_lookup or {}
    _record_equity(price_lookup)

    st.markdown("### Paper Trading Desk")
    st.caption("Simulation only. This never places real Angel One orders.")

    positions_df = _positions_frame(price_lookup)
    portfolio_value = _portfolio_value(price_lookup)
    unrealized = float(positions_df["Unrealized P&L"].sum()) if not positions_df.empty else 0.0
    total_pnl = st.session_state.paper_realized_pnl + unrealized

    col_cash, col_value, col_positions, col_pnl, col_risk = st.columns(5)
    with col_cash:
        st.metric("Cash", f"₹{st.session_state.paper_cash:,.2f}")
    with col_value:
        st.metric("Equity", f"₹{portfolio_value:,.2f}")
    with col_positions:
        st.metric("Open Positions", len(st.session_state.paper_positions))
    with col_pnl:
        st.metric("Total P&L", f"₹{total_pnl:,.2f}", delta=f"{(total_pnl / INITIAL_CASH) * 100:+.2f}%")
    with col_risk:
        deployed = portfolio_value - st.session_state.paper_cash
        st.metric("Deployed", f"₹{deployed:,.2f}", delta=f"{(deployed / max(portfolio_value, 1)) * 100:.1f}%")

    risk_rows = []
    for symbol, pos in list(st.session_state.paper_positions.items()):
        last_price = price_lookup.get(symbol, pos["avg_price"])
        stop_loss = pos.get("stop_loss")
        target = pos.get("target")
        if stop_loss and last_price <= stop_loss:
            risk_rows.append(f"{symbol}: stop loss touched at ₹{last_price:,.2f}")
        if target and last_price >= target:
            risk_rows.append(f"{symbol}: target touched at ₹{last_price:,.2f}")

    view = st.segmented_control(
        "Paper trading widgets",
        options=["Trade", "Positions", "Risk", "History"],
        default=st.session_state.get("paper_view", "Trade"),
        key="paper_view",
    )

    if view == "Trade":
        ticket_col, summary_col = st.columns([1.4, 1])
        with ticket_col:
            with st.container(border=True):
                st.subheader("Order Ticket")
                if not selected_stocks:
                    st.info("Select a stock from the sidebar to place a paper trade.")
                else:
                    labels = [f"{s['symbol']} ({s['exchange']})" for s in selected_stocks]
                    selected = st.selectbox("Symbol", labels)
                    symbol = selected.split(" (")[0]
                    live_price = float(price_lookup.get(symbol, 100.0))

                    with st.form("paper_order_ticket", clear_on_submit=False):
                        side = st.segmented_control("Side", options=["BUY", "SELL"], default="BUY")
                        c1, c2 = st.columns(2)
                        with c1:
                            order_type = st.selectbox("Order Type", ["Market", "Limit"])
                        with c2:
                            strategy = st.selectbox("Strategy", ["Manual", "RSI Momentum", "DMA Trend", "Breakout"])

                        c3, c4, c5 = st.columns(3)
                        with c3:
                            price = st.number_input("Price", min_value=0.01, value=live_price, step=0.05)
                        with c4:
                            stop_loss = st.number_input("Stop Loss", min_value=0.0, value=max(float(price) * 0.95, 0.0), step=0.05)
                        with c5:
                            target = st.number_input("Target", min_value=0.0, value=float(price) * 1.10, step=0.05)

                        risk_pct = st.slider("Risk per trade", min_value=0.1, max_value=10.0, value=DEFAULT_RISK_PCT, step=0.1, format="%.1f%%")
                        suggested_qty = _risk_quantity(price, stop_loss, portfolio_value, risk_pct)
                        qty = st.number_input("Quantity", min_value=1, value=suggested_qty, step=1)
                        notional = qty * price
                        st.caption(f"Estimated notional: {_fmt_money(notional)}")

                        submitted = st.form_submit_button("Place Paper Order", type="primary", use_container_width=True)
                        if submitted:
                            if side == "BUY":
                                ok, msg = _buy(symbol, qty, price, strategy, stop_loss, target)
                            else:
                                ok, msg = _sell(symbol, qty, price)
                            st.success(msg) if ok else st.error(msg)
                            _record_equity(price_lookup)

                    if order_type == "Limit":
                        st.caption("Paper limit orders fill immediately in this version.")

        with summary_col:
            with st.container(border=True):
                st.subheader("Trade Summary")
                if selected_stocks:
                    symbol = selected.split(" (")[0]
                    st.metric("Selected", symbol, _fmt_money(price_lookup.get(symbol)))
                st.metric("Suggested Qty", suggested_qty if selected_stocks else 0)
                st.metric("Risk Alerts", len(risk_rows))

    elif view == "Positions":
        st.subheader("Open Positions")
        positions_df = _positions_frame(price_lookup)
        if not positions_df.empty:
            _positions_table(positions_df)
        else:
            st.info("No open paper positions.")

    elif view == "Risk":
        risk_col, curve_col = st.columns([1, 1.4])
        with risk_col:
            with st.container(border=True):
                st.subheader("Risk Monitor")
                if risk_rows:
                    for row in risk_rows:
                        st.warning(row)
                else:
                    st.success("No stop-loss or target alerts right now.")
        with curve_col:
            st.subheader("Equity Curve")
            if st.session_state.paper_equity_curve:
                curve_df = pd.DataFrame(st.session_state.paper_equity_curve)
                st.line_chart(curve_df.set_index("Step")["Value"], height=280)
            else:
                st.info("Equity curve will appear after account changes.")

    elif view == "History":
        hist_col, action_col = st.columns([1.5, 0.7])
        with hist_col:
            st.subheader("Order History")
            if st.session_state.paper_orders:
                st.dataframe(pd.DataFrame(st.session_state.paper_orders), width="stretch", height=340, hide_index=True)
            else:
                st.info("No paper orders yet.")
        with action_col:
            with st.container(border=True):
                st.subheader("Account Actions")
                st.caption("Reset clears cash, positions, orders, P&L, and equity curve.")
                if st.button("Reset Paper Account", type="secondary", use_container_width=True):
                    st.session_state.paper_cash = INITIAL_CASH
                    st.session_state.paper_positions = {}
                    st.session_state.paper_orders = []
                    st.session_state.paper_realized_pnl = 0.0
                    st.session_state.paper_equity_curve = []
                    st.rerun()
