import pandas as pd
import numpy as np

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df.columns = [col.lower() for col in df.columns]
    
    # RSI Calculation (pure pandas)
    def calculate_rsi(series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    df['rsi_14'] = calculate_rsi(df['close'], 14)
    
    # EMA & SMA
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    df['sma_200'] = df['close'].rolling(window=200).mean()
    
    # MACD
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp12 - exp26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    return df

def check_screener_rules(row: pd.Series) -> list:
    triggers = []
    rsi = row.get('rsi_14')
    close = row.get('close')
    ema20 = row.get('ema_20')
    low = row.get('low')
    
    if pd.notna(rsi):
        if rsi > 70: triggers.append("RSI Overbought (>70)")
        elif rsi < 30: triggers.append("RSI Oversold (<30)")
    
    if pd.notna(ema20) and pd.notna(close) and pd.notna(low):
        if close > ema20 and low <= ema20:
            triggers.append("EMA-20 Dynamic Support Bounce")
    
    return triggers
