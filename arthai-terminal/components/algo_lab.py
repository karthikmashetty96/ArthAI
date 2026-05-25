import pandas as pd
import streamlit as st


STRATEGIES = {
    "DMA Trend": {
        "entry": "Close > DMA 50 and DMA 50 > DMA 200",
        "exit": "Close < DMA 50 or stop loss hit",
        "risk": "1% equity per trade, 8-10% max position size",
    },
    "RSI Momentum": {
        "entry": "RSI between 55 and 70 with price above DMA 50",
        "exit": "RSI falls below 50 or price closes below DMA 50",
        "risk": "Use previous swing low as stop loss",
    },
    "Breakout": {
        "entry": "Close breaks 20-day high with volume above 20-day average",
        "exit": "Failed breakout close or trailing stop",
        "risk": "Smaller size during high volatility",
    },
}


def render_algo_lab():
    st.subheader("Algo Lab")
    st.caption("Design and dry-run strategies here. Live order routing stays disabled until safety checks are complete.")

    col_strategy, col_safety = st.columns([2, 1])

    with col_strategy:
        strategy = st.selectbox("Strategy Template", list(STRATEGIES.keys()))
        config = STRATEGIES[strategy]

        st.markdown("#### Logic")
        c1, c2 = st.columns(2)
        with c1:
            st.text_area("Entry Rule", value=config["entry"], height=100)
        with c2:
            st.text_area("Exit Rule", value=config["exit"], height=100)

        st.markdown("#### Risk Controls")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.number_input("Risk / Trade %", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
        with r2:
            st.number_input("Max Positions", min_value=1, max_value=25, value=5, step=1)
        with r3:
            st.number_input("Max Position %", min_value=1.0, max_value=50.0, value=10.0, step=1.0)
        with r4:
            st.number_input("Daily Loss Limit %", min_value=0.5, max_value=10.0, value=2.0, step=0.5)

        st.markdown("#### Execution Mode")
        mode = st.radio(
            "Mode",
            ["Paper only", "Live disabled"],
            horizontal=True,
            help="Live trading is intentionally disabled until broker order flow, audit logs, and kill switch are implemented.",
        )
        if mode == "Live disabled":
            st.warning("Live trading is locked. Build confidence in paper mode first.")

    with col_safety:
        st.markdown("#### Go-Live Checklist")
        checklist = {
            "Paper trading profitable for 30+ sessions": False,
            "Max drawdown understood": False,
            "Order logs stored locally": False,
            "Kill switch tested": False,
            "Angel order placement tested with 1-share sandbox-sized trades": False,
            "Telegram failure alerts tested": False,
        }
        for label, value in checklist.items():
            st.checkbox(label, value=value, disabled=True)

        st.markdown("#### Suggested Build Order")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Phase": "1", "Capability": "Paper trading + logs", "Status": "Now"},
                    {"Phase": "2", "Capability": "Backtesting", "Status": "Next"},
                    {"Phase": "3", "Capability": "Forward test alerts", "Status": "Next"},
                    {"Phase": "4", "Capability": "One-click live order", "Status": "Later"},
                    {"Phase": "5", "Capability": "Fully automated live trading", "Status": "Last"},
                ]
            ),
            width="stretch",
            height=230,
        )
