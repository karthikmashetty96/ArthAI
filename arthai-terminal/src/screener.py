import math
import re
import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd
import yfinance as yf

from src.indicators import calculate_technical_indicators

logger = logging.getLogger(__name__)


FIELD_ALIASES = {
    "market capitalization": "market_cap_cr",
    "market cap": "market_cap_cr",
    "current price": "current_price",
    "price": "current_price",
    "dma 50": "dma_50",
    "sma 50": "dma_50",
    "dma 200": "dma_200",
    "sma 200": "dma_200",
    "rsi": "rsi_14",
    "rsi 14": "rsi_14",
    "sales growth 3years": "sales_growth_3y",
    "sales growth 3 years": "sales_growth_3y",
    "profit growth 3years": "profit_growth_3y",
    "profit growth 3 years": "profit_growth_3y",
    "yoy quarterly profit growth": "yoy_quarterly_profit_growth",
    "yoy quarterly sales growth": "yoy_quarterly_sales_growth",
    "debt to equity": "debt_to_equity",
    "return on capital employed": "roce",
    "roce": "roce",
    "promoter holding": "promoter_holding",
    "volume": "volume",
}

DISPLAY_NAMES = {
    "market_cap_cr": "Market Cap (Cr)",
    "current_price": "Price",
    "dma_50": "DMA 50",
    "dma_200": "DMA 200",
    "rsi_14": "RSI",
    "sales_growth_3y": "Sales Growth 3Y %",
    "profit_growth_3y": "Profit Growth 3Y %",
    "yoy_quarterly_profit_growth": "YOY Q Profit %",
    "yoy_quarterly_sales_growth": "YOY Q Sales %",
    "debt_to_equity": "Debt/Equity",
    "roce": "ROCE %",
    "promoter_holding": "Promoter %",
    "volume": "Volume",
}


@dataclass
class ScreenerCondition:
    left: str
    op: str
    right: str
    raw: str


def _normalize_field(text: str) -> str:
    key = re.sub(r"\s+", " ", text.strip().lower())
    key = key.replace("_", " ")
    return FIELD_ALIASES.get(key, key.replace(" ", "_"))


def parse_screener_query(query: str) -> list[ScreenerCondition]:
    """Parse simple Screener.in-style conditions joined by AND."""
    cleaned = query.replace("\r", "\n")
    pieces = []
    for line in cleaned.splitlines():
        line = line.strip()
        if not line:
            continue
        pieces.extend(part.strip() for part in re.split(r"\bAND\b", line, flags=re.IGNORECASE) if part.strip())

    conditions = []
    for raw in pieces:
        match = re.match(r"(.+?)\s*(>=|<=|>|<|==|=)\s*(.+)", raw)
        if not match:
            raise ValueError(f"Could not parse condition: {raw}")
        left, op, right = match.groups()
        conditions.append(ScreenerCondition(_normalize_field(left), "==" if op == "=" else op, right.strip(), raw))
    return conditions


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return math.nan
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _growth_percent(current: float, previous: float) -> float:
    if not previous or pd.isna(previous):
        return math.nan
    return ((current - previous) / abs(previous)) * 100


def _statement_value(statement: pd.DataFrame, labels: list[str], col_index: int) -> float:
    if statement is None or statement.empty or len(statement.columns) <= col_index:
        return math.nan
    for label in labels:
        if label in statement.index:
            return _safe_float(statement.iloc[statement.index.get_loc(label), col_index])
    return math.nan


def _resolve_operand(expr: str, metrics: dict[str, float]) -> float:
    expr = expr.strip()
    if "*" in expr:
        result = 1.0
        for part in expr.split("*"):
            result *= _resolve_operand(part, metrics)
        return result

    field = _normalize_field(expr)
    if field in metrics:
        return _safe_float(metrics[field])
    return _safe_float(expr)


def condition_passes(condition: ScreenerCondition, metrics: dict[str, float]) -> tuple[bool, str | None]:
    left = _safe_float(metrics.get(condition.left))
    right = _resolve_operand(condition.right, metrics)

    if pd.isna(left):
        return False, condition.left
    if pd.isna(right):
        return False, condition.right

    if condition.op == ">":
        return left > right, None
    if condition.op == "<":
        return left < right, None
    if condition.op == ">=":
        return left >= right, None
    if condition.op == "<=":
        return left <= right, None
    if condition.op == "==":
        return left == right, None
    raise ValueError(f"Unsupported operator: {condition.op}")


def symbol_for_yahoo(stock: dict) -> str:
    symbol = (stock.get("symbol") or stock.get("tradingsymbol") or "").upper().replace("-EQ", "")
    exchange = stock.get("exchange") or stock.get("exch") or "NSE"
    if symbol in {"NIFTY", "NIFTY 50"}:
        return "^NSEI"
    if symbol == "SENSEX":
        return "^BSESN"
    suffix = ".BO" if exchange == "BSE" else ".NS"
    return f"{symbol}{suffix}"


def fetch_screener_metrics(stock: dict) -> dict[str, float | str]:
    """Fetch technical/fundamental metrics for one stock with error handling."""
    ticker_symbol = symbol_for_yahoo(stock)
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="1y", interval="1d")
        if hist.empty:
            raise ValueError("No price history")

        hist = hist.rename(columns={col: col.lower() for col in hist.columns}).reset_index()
        tech = calculate_technical_indicators(hist)
        
        if tech.empty or len(tech) == 0:
            raise ValueError("No technical indicators calculated")
        
        latest = tech.iloc[-1]

        info = ticker.info or {}
        market_cap = _safe_float(info.get("marketCap"))
        debt_to_equity = _safe_float(info.get("debtToEquity"))
        if debt_to_equity > 10:
            debt_to_equity = debt_to_equity / 100

        _financials = ticker.financials
        financials = _financials if isinstance(_financials, pd.DataFrame) and not _financials.empty else pd.DataFrame()
        _quarterly = ticker.quarterly_financials
        quarterly = _quarterly if isinstance(_quarterly, pd.DataFrame) and not _quarterly.empty else pd.DataFrame()
        current_sales = _statement_value(financials, ["Total Revenue"], 0)
        old_sales = _statement_value(financials, ["Total Revenue"], 3)
        current_profit = _statement_value(financials, ["Net Income"], 0)
        old_profit = _statement_value(financials, ["Net Income"], 3)
        current_q_sales = _statement_value(quarterly, ["Total Revenue"], 0)
        prior_year_q_sales = _statement_value(quarterly, ["Total Revenue"], 4)
        current_q_profit = _statement_value(quarterly, ["Net Income"], 0)
        prior_year_q_profit = _statement_value(quarterly, ["Net Income"], 4)

        promoter_holding = _safe_float(info.get("heldPercentInsiders"))
        if promoter_holding <= 1:
            promoter_holding *= 100

        roce = _safe_float(info.get("returnOnCapitalEmployed"))
        if pd.isna(roce):
            roce = _safe_float(info.get("returnOnAssets"))
        if roce <= 1:
            roce *= 100

        return {
            "symbol": stock.get("symbol"),
            "name": stock.get("name"),
            "exchange": stock.get("exchange") or stock.get("exch"),
            "market_cap_cr": market_cap / 10_000_000 if market_cap and not math.isnan(market_cap) else math.nan,
            "current_price": _safe_float(latest.get("close")),
            "dma_50": _safe_float(latest.get("sma_50")),
            "dma_200": _safe_float(latest.get("sma_200")),
            "rsi_14": _safe_float(latest.get("rsi_14")),
            "sales_growth_3y": _growth_percent(current_sales, old_sales),
            "profit_growth_3y": _growth_percent(current_profit, old_profit),
            "yoy_quarterly_profit_growth": _growth_percent(current_q_profit, prior_year_q_profit),
            "yoy_quarterly_sales_growth": _growth_percent(current_q_sales, prior_year_q_sales),
            "debt_to_equity": debt_to_equity,
            "roce": roce,
            "promoter_holding": promoter_holding,
            "volume": _safe_float(latest.get("volume")),
        }
    except KeyError as ke:
        logger.error(f"Missing data key for {ticker_symbol}: {ke}")
        raise
    except TypeError as te:
        logger.error(f"Type error processing {ticker_symbol}: {te}")
        raise
    except Exception as e:
        logger.error(f"Error fetching metrics for {ticker_symbol}: {e}")
        raise


def metrics_to_display_row(metrics: dict[str, float | str]) -> dict[str, Any]:
    row = {
        "Symbol": metrics.get("symbol"),
        "Name": metrics.get("name"),
        "Exchange": metrics.get("exchange"),
    }
    for key, label in DISPLAY_NAMES.items():
        row[label] = metrics.get(key)
    return row
