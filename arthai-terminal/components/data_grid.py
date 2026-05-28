# components/data_grid.py
import streamlit as st
import pandas as pd

def render_data_grid(df: pd.DataFrame) -> pd.DataFrame:
    """
    Render a professional data grid for screening results.
    
    Args:
        df: DataFrame with columns from app.py screener results
    
    Returns:
        DataFrame rows with alerts (for Telegram dispatch)
    """
    if df.empty:
        st.info("No results to display.")
        return pd.DataFrame()
    
    # ─────────────────────────────────────────────────────────────────────
    # 🎨 Prepare Display DataFrame (no re-formatting of already-formatted cols)
    # ─────────────────────────────────────────────────────────────────────
    
    display_df = df.copy()
    
    # Only format numeric columns that aren't already strings
    # Skip "Price (₹)", "RSI", "EMA20" if they're already formatted strings
    for col in ["RSI", "EMA20"]:
        if col in display_df.columns and display_df[col].dtype in ['float64', 'int64', 'float32', 'int32']:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
    
    # ─────────────────────────────────────────────────────────────────────
    # 🎨 Conditional Styling (safe checks for column existence + type)
    # ─────────────────────────────────────────────────────────────────────
    
    style_subsets = []

    # Style RSI: green for <30, red for >70
    if "RSI" in display_df.columns:
        def rsi_style(val):
            try:
                # Handle both string and numeric values
                if isinstance(val, str):
                    rsi = float(val.replace(',', '')) if val.replace(',', '').replace('.', '', 1).replace('-', '', 1).isdigit() else 50
                else:
                    rsi = float(val) if pd.notna(val) else 50
                
                if rsi < 30:
                    return "background-color: rgba(16, 185, 129, 0.18); color: #34d399; font-weight: 700; border-radius: 4px;"
                elif rsi > 70:
                    return "background-color: rgba(244, 63, 94, 0.18); color: #fb7185; font-weight: 700; border-radius: 4px;"
                return "color: #cbd5e1;"
            except:
                return ""

        style_subsets.append((rsi_style, ["RSI"]))

    # Style Alerts: highlight if not empty
    if "Alerts" in display_df.columns:
        def alert_style(val):
            if val and str(val).strip() and val != "":
                return "background-color: rgba(6, 182, 212, 0.12); color: #22d3ee; font-weight: 600; border-left: 3px solid #06b6d4;"
            return ""

        style_subsets.append((alert_style, ["Alerts"]))
    
    # ─────────────────────────────────────────────────────────────────────
    # Render Data Grid
    # ─────────────────────────────────────────────────────────────────────
    
    st.subheader("Screening Results")
    st.caption("Filtered trade candidates")
    
    # Hide internal columns (starting with _)
    display_cols = [c for c in display_df.columns if not c.startswith("_")]
    render_df = display_df[display_cols]

    # Render with or without styling
    try:
        if style_subsets:
            styled = render_df.style
            for style_func, subset in style_subsets:
                visible_subset = [col for col in subset if col in display_cols]
                if visible_subset:
                    styled = styled.map(style_func, subset=visible_subset)
            st.dataframe(
                styled,
                width="stretch",
                height=460,
                hide_index=True,
                column_config={
                    "Symbol": st.column_config.TextColumn("Symbol", width="small"),
                    "Exchange": st.column_config.TextColumn("Exch", width="small"),
                    "Type": st.column_config.TextColumn("Type", width="small"),
                    "Price (₹)": st.column_config.TextColumn("LTP", width="small"),
                    "RSI": st.column_config.TextColumn("RSI", width="small"),
                    "EMA20": st.column_config.TextColumn("EMA 20", width="small"),
                    "Alerts": st.column_config.TextColumn("Signals", width="large"),
                },
            )
        else:
            st.dataframe(render_df, width="stretch", height=460, hide_index=True)
    except Exception as e:
        # Fallback to plain dataframe if styling fails
        st.warning(f"Styling issue: {e}. Showing plain table.")
        st.dataframe(render_df, width="stretch", height=460, hide_index=True)
    
    # ─────────────────────────────────────────────────────────────────────
    # Return Alert Rows for Telegram Dispatch
    # ─────────────────────────────────────────────────────────────────────
    
    if "Alerts" in display_df.columns:
        alert_rows = display_df[display_df["Alerts"].astype(str).str.strip() != ""]
    else:
        alert_rows = pd.DataFrame()
    
    return alert_rows
