#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.angel_client import AngelOneClient


def main() -> int:
    print("=== Angel One Direct HTTP Test ===")
    client = AngelOneClient()

    if not client.login():
        print("❌ Login failed")
        return 1

    print("✅ Login successful")

    # Test a few stocks
    test_stocks = [("RELIANCE", "NSE"), ("TCS", "NSE"), ("500325", "BSE")]
    for symbol, exchange in test_stocks:
        quote = client.get_quote(symbol, exchange)
        if quote:
            print(f"✅ {symbol} ({exchange}): Rs. {quote['price']} ({quote['change_pct']}%)")
            return 0
        print(f"❌ {symbol} ({exchange}): Failed")

    return 1


if __name__ == "__main__":
    sys.exit(main())
