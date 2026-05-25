# src/ai_reasoning.py
# pyright: reportAttributeAccessIssue=false
import logging
import pandas as pd
from src.config import settings

logger = logging.getLogger(__name__)

def generate_ai_trade_plan(
    ticker: str, 
    tech_df: pd.DataFrame | None = None,
    focus: str = "momentum"
) -> str:
    """
    Generate AI trade analysis using local Ollama model.
    
    Args:
        ticker: Stock symbol (e.g., "RELIANCE", "TCS")
        tech_df: Technical indicators DataFrame (optional)
        focus: Analysis focus: "momentum", "support", "breakout", "reversal"
    
    Returns:
        AI-generated trade plan as string
    """
    # Guard: ticker must be non-empty string
    if not ticker or not isinstance(ticker, str):
        return "⚠️ Invalid ticker provided"
    
    # Build context from technical data
    if tech_df is None or tech_df.empty:
        context = f"Basic analysis for {ticker} with limited data."
    else:
        try:
            latest = tech_df.iloc[-1]
            rsi = latest.get('rsi_14', latest.get('RSI_14', 50))
            ema20 = latest.get('ema_20', latest.get('EMA_20', 0))
            sma50 = latest.get('sma_50', latest.get('SMA_50', 0))
            price = latest.get('close', latest.get('Close', 0))
            
            # Simple signal detection
            signals = []
            if rsi < 30:
                signals.append("RSI oversold (<30)")
            elif rsi > 70:
                signals.append("RSI overbought (>70)")
            if ema20 > sma50:
                signals.append("EMA20 > SMA50 (bullish)")
            elif ema20 < sma50:
                signals.append("EMA20 < SMA50 (bearish)")
            
            signal_str = "; ".join(signals) if signals else "No clear signals"
            context = f"{ticker} @ ₹{price:.2f}: RSI={rsi:.1f}, EMA20={ema20:.1f}, SMA50={sma50:.1f}. Signals: {signal_str}"
        except Exception as e:
            logger.warning(f"Failed to parse tech_df for {ticker}: {e}")
            context = f"Basic analysis for {ticker} (data parse error)"
    
    # Guard: Ensure Ollama settings are valid strings
    base_url = getattr(settings, 'ollama_base_url', None) or "http://localhost:11434"
    model = getattr(settings, 'ollama_model', None) or "llama3"
    
    try:
        import ollama
        
        # Build prompt
        system_prompt = "You are a professional Indian stock market analyst. Provide concise, actionable trade ideas with entry/exit levels and risk management. Use INR for prices."
        user_prompt = f"Analyze: {context}\nFocus area: {focus}\n\nProvide: 1) Bias (bullish/bearish/neutral), 2) Entry zone, 3) Target, 4) Stop loss, 5) Key levels."
        
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            options={"temperature": 0.3, "num_predict": 500}
        )
        
        content = response.get('message', {}).get('content', '').strip()
        return content if content else f"⚠️ Empty response from Ollama for {ticker}"
        
    except ImportError:
        logger.warning("ollama package not installed. Install with: pip install ollama")
        return f"⚠️ AI analysis unavailable (ollama not installed). Context: {context}"
    except Exception as e:
        logger.error(f"Ollama error for {ticker}: {e}")
        return f"⚠️ AI analysis unavailable. {ticker} context: {context}"


def format_ai_response(raw_text: str, ticker: str) -> dict:
    """
    Parse raw AI response into structured dict for UI display.
    
    Args:
        raw_text: Raw string from generate_ai_trade_plan()
        ticker: Stock symbol for reference
    
    Returns:
        dict with parsed fields
    """
    # Simple fallback parsing (can be enhanced with regex/NLP)
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    
    return {
        "ticker": ticker,
        "raw_response": raw_text,
        "summary": lines[0] if lines else "No summary",
        "key_points": [l for l in lines[1:6] if l.startswith(('•', '-', '1)', '2)', 'Entry', 'Target', 'Stop'))],
        "confidence": "medium"  # Could be extracted from response with more parsing
    }