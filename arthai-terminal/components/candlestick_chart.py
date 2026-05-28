import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from src.data_engine import fetch_historical_candles
from src.indicators import calculate_technical_indicators

def _add_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    df = df.copy()
    mid = df["close"].rolling(window=period).mean()
    std = df["close"].rolling(window=period).std()
    df["bb_mid"] = mid
    df["bb_upper"] = mid + (std_dev * std)
    df["bb_lower"] = mid - (std_dev * std)
    return df


def _add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_volume = df["volume"].replace(0, pd.NA).cumsum()
    df["vwap"] = (typical_price * df["volume"]).cumsum() / cumulative_volume
    return df


def render_chart(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    overlays: list[str] | None = None,
    lower_indicators: list[str] | None = None,
    dark_mode: bool = True,
) -> pd.DataFrame:
    st.subheader(f"{ticker} Price Action")
    overlays = overlays or ["EMA 20", "SMA 50"]
    lower_indicators = lower_indicators or ["Volume", "RSI", "MACD"]

    df = fetch_historical_candles(ticker, period=period, interval=interval)
    if df.empty:
        st.warning("No historical data available.")
        return pd.DataFrame()

    df = calculate_technical_indicators(df)
    if "Bollinger Bands" in overlays:
        df = _add_bollinger_bands(df)
    if "VWAP" in overlays and "volume" in df.columns:
        df = _add_vwap(df)

    row_count = 1 + len(lower_indicators)
    row_heights = [0.58] + [0.42 / max(len(lower_indicators), 1)] * len(lower_indicators)

    fig = make_subplots(
        rows=row_count,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
    )

    # Theme adaptive colors
    green_color = "#10b981" if dark_mode else "#0f8a5f"
    red_color = "#f43f5e" if dark_mode else "#c2413a"
    chart_template = "plotly_dark" if dark_mode else "plotly_white"
    paper_bg = "rgba(15, 23, 42, 0.2)" if dark_mode else "rgba(255, 255, 255, 0.4)"
    plot_bg = "rgba(11, 19, 31, 0.4)" if dark_mode else "rgba(240, 244, 248, 0.4)"
    font_color = "#cbd5e1" if dark_mode else "#1e293b"
    grid_color = "#1e293b" if dark_mode else "#cbd5e1"
    macd_hist_color = "#334155" if dark_mode else "#94a3b8"
    macd_line_color = "#06b6d4" if dark_mode else "#0f766e"
    signal_line_color = "#fbbf24" if dark_mode else "#b7791f"

    fig.add_trace(go.Candlestick(
        x=df['date'], open=df['open'], high=df['high'],
        low=df['low'], close=df['close'], name="OHLC",
        increasing_line_color=green_color,
        decreasing_line_color=red_color,
        increasing_fillcolor=green_color,
        decreasing_fillcolor=red_color,
    ), row=1, col=1)

    if "EMA 20" in overlays and 'ema_20' in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['ema_20'], line=dict(color="#38bdf8", width=1.5), name="20 EMA"), row=1, col=1)
    if "SMA 50" in overlays and 'sma_50' in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['sma_50'], line=dict(color=signal_line_color, width=1.5), name="50 DMA"), row=1, col=1)
    if "SMA 200" in overlays and 'sma_200' in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['sma_200'], line=dict(color="#ec4899", width=1.5), name="200 DMA"), row=1, col=1)
    if "Bollinger Bands" in overlays:
        fig.add_trace(go.Scatter(x=df['date'], y=df['bb_upper'], line=dict(color="#64748b", width=1), name="BB Upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['bb_lower'], line=dict(color="#64748b", width=1), fill='tonexty', fillcolor='rgba(100, 116, 139, 0.1)', name="BB Lower"), row=1, col=1)
    if "VWAP" in overlays and "vwap" in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['vwap'], line=dict(color="#a855f7", width=1.4), name="VWAP"), row=1, col=1)

    current_row = 2
    for indicator in lower_indicators:
        if indicator == "Volume" and "volume" in df.columns:
            colors = [green_color if close >= open_ else red_color for close, open_ in zip(df["close"], df["open"])]
            fig.add_trace(go.Bar(x=df["date"], y=df["volume"], marker_color=colors, name="Volume"), row=current_row, col=1)
        elif indicator == "RSI" and "rsi_14" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["rsi_14"], line=dict(color=macd_line_color, width=1.5), name="RSI 14"), row=current_row, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color=red_color, row=current_row, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color=green_color, row=current_row, col=1)
        elif indicator == "MACD" and {"macd", "macd_signal", "macd_hist"}.issubset(df.columns):
            fig.add_trace(go.Bar(x=df["date"], y=df["macd_hist"], marker_color=macd_hist_color, name="MACD Hist"), row=current_row, col=1)
            fig.add_trace(go.Scatter(x=df["date"], y=df["macd"], line=dict(color=macd_line_color, width=1.3), name="MACD"), row=current_row, col=1)
            fig.add_trace(go.Scatter(x=df["date"], y=df["macd_signal"], line=dict(color=signal_line_color, width=1.3), name="Signal"), row=current_row, col=1)
        current_row += 1

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=720,
        template=chart_template,
        paper_bgcolor=paper_bg,
        plot_bgcolor=plot_bg,
        font=dict(color=font_color, family="Outfit, Inter, sans-serif"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    fig.update_xaxes(
        gridcolor=grid_color,
        zerolinecolor=grid_color,
        tickfont=dict(family="JetBrains Mono, monospace")
    )
    fig.update_yaxes(
        gridcolor=grid_color,
        zerolinecolor=grid_color,
        tickfont=dict(family="JetBrains Mono, monospace")
    )
    st.plotly_chart(fig, width="stretch")
    return df
