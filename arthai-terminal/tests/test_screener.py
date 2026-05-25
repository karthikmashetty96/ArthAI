"""Unit tests for screener.py - Tests for parsing and filtering logic."""

import pytest
import math
import pandas as pd
from src.screener import (
    parse_screener_query,
    condition_passes,
    _normalize_field,
    _safe_float,
    _growth_percent,
)


class TestFieldNormalization:
    """Test field name normalization."""

    def test_normalize_market_cap(self):
        assert _normalize_field("market capitalization") == "market_cap_cr"
        assert _normalize_field("Market Cap") == "market_cap_cr"
        assert _normalize_field("MARKET CAP") == "market_cap_cr"

    def test_normalize_price(self):
        assert _normalize_field("Current Price") == "current_price"
        assert _normalize_field("price") == "current_price"

    def test_normalize_dma(self):
        assert _normalize_field("DMA 50") == "dma_50"
        assert _normalize_field("SMA 50") == "dma_50"
        assert _normalize_field("dma 200") == "dma_200"

    def test_normalize_rsi(self):
        assert _normalize_field("RSI") == "rsi_14"
        assert _normalize_field("RSI 14") == "rsi_14"

    def test_unknown_field(self):
        assert _normalize_field("unknown_metric") == "unknown_metric"


class TestQueryParsing:
    """Test screener query parsing."""

    def test_parse_single_condition(self):
        query = "Current Price > 100"
        conditions = parse_screener_query(query)
        assert len(conditions) == 1
        assert conditions[0].left == "current_price"
        assert conditions[0].op == ">"
        assert conditions[0].right == "100"

    def test_parse_multiple_conditions(self):
        query = """Current Price > 100 AND
        DMA 50 > DMA 200 AND
        RSI > 55"""
        conditions = parse_screener_query(query)
        assert len(conditions) == 3
        assert conditions[0].left == "current_price"
        assert conditions[1].left == "dma_50"
        assert conditions[1].right == "DMA 200"  # Right side preserves case unless it's a field alias
        assert conditions[2].left == "rsi_14"

    def test_parse_comparison_operators(self):
        tests = [
            ("Price > 100", ">"),
            ("Price < 500", "<"),
            ("Price >= 100", ">="),
            ("Price <= 500", "<="),
            ("Price == 250", "=="),
            ("Price = 250", "=="),  # = should convert to ==
        ]
        for query, expected_op in tests:
            conditions = parse_screener_query(query)
            assert conditions[0].op == expected_op

    def test_parse_invalid_condition(self):
        with pytest.raises(ValueError):
            parse_screener_query("Invalid condition without operator")


class TestSafeFloat:
    """Test safe float conversion."""

    def test_safe_float_valid(self):
        assert _safe_float("100.5") == 100.5
        assert _safe_float(100.5) == 100.5
        assert _safe_float("100") == 100.0

    def test_safe_float_with_comma(self):
        assert _safe_float("1,000.5") == 1000.5
        assert _safe_float("10,00,000") == 1000000.0

    def test_safe_float_with_percent(self):
        assert _safe_float("50%") == 50.0

    def test_safe_float_invalid(self):
        assert math.isnan(_safe_float("invalid"))
        assert math.isnan(_safe_float(None))
        assert math.isnan(_safe_float(""))

    def test_safe_float_zero(self):
        assert _safe_float("0") == 0.0
        assert _safe_float(0) == 0.0


class TestGrowthPercent:
    """Test growth percentage calculation."""

    def test_growth_percent_positive(self):
        assert _growth_percent(120, 100) == 20.0
        assert _growth_percent(150, 100) == 50.0

    def test_growth_percent_negative(self):
        assert _growth_percent(80, 100) == -20.0

    def test_growth_percent_zero_previous(self):
        assert math.isnan(_growth_percent(100, 0))
        assert math.isnan(_growth_percent(100, None))

    def test_growth_percent_zero_current(self):
        assert _growth_percent(0, 100) == -100.0


class TestConditionPasses:
    """Test condition evaluation."""

    def _make_condition(self, left: str, op: str, right: str):
        """Helper to create a ScreenerCondition."""
        from src.screener import ScreenerCondition
        return ScreenerCondition(left, op, right, f"{left} {op} {right}")

    def test_greater_than(self):
        metrics = {"price": 150}
        cond = self._make_condition("price", ">", "100")
        assert condition_passes(cond, metrics)[0] is True
        cond = self._make_condition("price", ">", "150")
        assert condition_passes(cond, metrics)[0] is False
        cond = self._make_condition("price", ">", "200")
        assert condition_passes(cond, metrics)[0] is False

    def test_less_than(self):
        metrics = {"price": 150}
        cond = self._make_condition("price", "<", "200")
        assert condition_passes(cond, metrics)[0] is True
        cond = self._make_condition("price", "<", "150")
        assert condition_passes(cond, metrics)[0] is False

    def test_greater_equal(self):
        metrics = {"price": 150}
        cond = self._make_condition("price", ">=", "150")
        assert condition_passes(cond, metrics)[0] is True
        cond = self._make_condition("price", ">=", "100")
        assert condition_passes(cond, metrics)[0] is True
        cond = self._make_condition("price", ">=", "200")
        assert condition_passes(cond, metrics)[0] is False

    def test_less_equal(self):
        metrics = {"price": 150}
        cond = self._make_condition("price", "<=", "150")
        assert condition_passes(cond, metrics)[0] is True
        cond = self._make_condition("price", "<=", "200")
        assert condition_passes(cond, metrics)[0] is True
        cond = self._make_condition("price", "<=", "100")
        assert condition_passes(cond, metrics)[0] is False

    def test_equal(self):
        metrics = {"price": 150}
        cond = self._make_condition("price", "==", "150")
        assert condition_passes(cond, metrics)[0] is True
        cond = self._make_condition("price", "==", "100")
        assert condition_passes(cond, metrics)[0] is False

    def test_missing_key(self):
        metrics = {"price": 150}
        cond = self._make_condition("missing_key", ">", "100")
        assert condition_passes(cond, metrics)[0] is False

    def test_nan_value(self):
        metrics = {"price": math.nan}
        cond = self._make_condition("price", ">", "100")
        assert condition_passes(cond, metrics)[0] is False

    def test_with_real_metrics(self):
        metrics = {
            "current_price": 250,
            "dma_50": 240,
            "dma_200": 200,
            "rsi_14": 65,
            "market_cap_cr": 50000,
        }
        cond = self._make_condition("current_price", ">", "100")
        assert condition_passes(cond, metrics)[0] is True
        cond = self._make_condition("dma_50", ">", "dma_200")
        assert condition_passes(cond, metrics)[0] is True
        cond = self._make_condition("rsi_14", "<", "70")
        assert condition_passes(cond, metrics)[0] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
