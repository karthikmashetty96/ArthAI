import streamlit as st
import pandas as pd
from src.ai_reasoning import generate_ai_trade_plan

def render_ai_panel(ticker: str, tech_df: pd.DataFrame):
    st.subheader("AI Trade Analysis")
    if tech_df is None or tech_df.empty:
        st.info("Waiting for live data...")
        return

    if st.button(f"Run AI Analysis for {ticker}"):
        with st.spinner("Querying local LLM..."):
            result = generate_ai_trade_plan(ticker=ticker, tech_df=tech_df)
            st.markdown(result)
