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

    fig.add_trace(go.Candlestick(
        x=df['date'], open=df['open'], high=df['high'],
        low=df['low'], close=df['close'], name="OHLC",
        increasing_line_color="#0f8a5f",
        decreasing_line_color="#c2413a",
        increasing_fillcolor="#0f8a5f",
        decreasing_fillcolor="#c2413a",
    ), row=1, col=1)

    if "EMA 20" in overlays and 'ema_20' in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['ema_20'], line=dict(color="#b7791f", width=1.5), name="20 EMA"), row=1, col=1)
    if "SMA 50" in overlays and 'sma_50' in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['sma_50'], line=dict(color="#2563eb", width=1.5), name="50 DMA"), row=1, col=1)
    if "SMA 200" in overlays and 'sma_200' in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['sma_200'], line=dict(color="#475569", width=1.5), name="200 DMA"), row=1, col=1)
    if "Bollinger Bands" in overlays:
        fig.add_trace(go.Scatter(x=df['date'], y=df['bb_upper'], line=dict(color="#94a3b8", width=1), name="BB Upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['bb_lower'], line=dict(color="#94a3b8", width=1), fill='tonexty', fillcolor='rgba(148,163,184,0.14)', name="BB Lower"), row=1, col=1)
    if "VWAP" in overlays and "vwap" in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['vwap'], line=dict(color="#0f766e", width=1.4), name="VWAP"), row=1, col=1)

    current_row = 2
    for indicator in lower_indicators:
        if indicator == "Volume" and "volume" in df.columns:
            colors = ["#0f8a5f" if close >= open_ else "#c2413a" for close, open_ in zip(df["close"], df["open"])]
            fig.add_trace(go.Bar(x=df["date"], y=df["volume"], marker_color=colors, name="Volume"), row=current_row, col=1)
        elif indicator == "RSI" and "rsi_14" in df.columns:
            fig.add_trace(go.Scatter(x=df["date"], y=df["rsi_14"], line=dict(color="#0f766e", width=1.5), name="RSI 14"), row=current_row, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="#c2413a", row=current_row, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="#0f8a5f", row=current_row, col=1)
        elif indicator == "MACD" and {"macd", "macd_signal", "macd_hist"}.issubset(df.columns):
            fig.add_trace(go.Bar(x=df["date"], y=df["macd_hist"], marker_color="#cbd5e1", name="MACD Hist"), row=current_row, col=1)
            fig.add_trace(go.Scatter(x=df["date"], y=df["macd"], line=dict(color="#102025", width=1.3), name="MACD"), row=current_row, col=1)
            fig.add_trace(go.Scatter(x=df["date"], y=df["macd_signal"], line=dict(color="#b7791f", width=1.3), name="Signal"), row=current_row, col=1)
        current_row += 1

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=720,
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#101820", family="Inter"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    fig.update_xaxes(gridcolor="#edf2f5", zerolinecolor="#edf2f5")
    fig.update_yaxes(gridcolor="#edf2f5", zerolinecolor="#edf2f5")
    st.plotly_chart(fig, width="stretch")
    return df
