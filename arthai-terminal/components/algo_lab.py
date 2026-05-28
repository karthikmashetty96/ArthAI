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
        st.markdown("#### 🛡️ Compliance Checklist")
        checklist = [
            ("Paper trading profitable (30+ sessions)", False),
            ("Max drawdown margins mapped", False),
            ("Structured audit logging verified", False),
            ("Execution Kill-switch validated", False),
            ("Angel One sandbox orders verified", False),
            ("Telegram alerts operational", False),
        ]
        for label, checked in checklist:
            status_text = "PASSED" if checked else "LOCKED"
            badge_class = "badge-buy" if checked else "badge-sell"
            st.markdown(f"""
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.55rem 0.75rem; background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.04); border-radius: 8px; margin-bottom: 0.5rem; backdrop-filter: blur(10px);">
                <span style="font-size: 0.82rem; color: #cbd5e1;">{label}</span>
                <span class="pro-badge {badge_class}" style="font-size: 0.65rem; border-color: rgba(255,255,255,0.02);">{status_text}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### 📈 Build Roadmap Phases")
        phases = [
            {"Phase": "Phase 1", "Capability": "Simulated Dry-Run Sandbox", "Status": "COMPLETED", "color": "#10b981", "badge": "badge-buy"},
            {"Phase": "Phase 2", "Capability": "Quantitative Backtest Engine", "Status": "IN QUEUE", "color": "#06b6d4", "badge": "badge-buy"},
            {"Phase": "Phase 3", "Capability": "Forward Breakout Alert Streams", "Status": "IN QUEUE", "color": "#06b6d4", "badge": "badge-buy"},
            {"Phase": "Phase 4", "Capability": "One-Click Instant Execution", "Status": "LOCKED", "color": "#f43f5e", "badge": "badge-sell"},
            {"Phase": "Phase 5", "Capability": "Autonomous Algorithmic Agent", "Status": "LOCKED", "color": "#f43f5e", "badge": "badge-sell"},
        ]
        for p in phases:
            st.markdown(f"""
            <div style="padding: 0.65rem 0.85rem; background: rgba(15, 23, 42, 0.35); border-left: 3px solid {p['color']}; border-top: 1px solid rgba(255,255,255,0.03); border-right: 1px solid rgba(255,255,255,0.03); border-bottom: 1px solid rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 0.55rem; display: flex; justify-content: space-between; align-items: center; backdrop-filter: blur(10px);">
                <div>
                    <div style="font-size: 0.7rem; color: #64748b; font-weight: 700; text-transform: uppercase;">{p['Phase']}</div>
                    <div style="font-size: 0.8rem; color: #f8fafc; font-weight: 600;">{p['Capability']}</div>
                </div>
                <span class="pro-badge {p['badge']}" style="font-size: 0.65rem; border-color: rgba(255,255,255,0.02);">{p['Status']}</span>
            </div>
            """, unsafe_allow_html=True)
