#!/usr/bin/env python3
import os
import sys
import time

import pyotp
from dotenv import load_dotenv


def main() -> int:
    from SmartApi import SmartConnect

    load_dotenv()

    api_key = os.getenv("ANGEL_API_KEY")
    mpin = os.getenv("ANGEL_API_SECRET")
    client_code = os.getenv("ANGEL_CLIENT_CODE")
    totp_secret = os.getenv("ANGEL_TOTP_SECRET")

    print("Testing Angel One Auth...")
    if not all([api_key, mpin, client_code, totp_secret]):
        print("Missing credentials in .env")
        return 1

    smartapi = SmartConnect(api_key=api_key)
    totp = pyotp.TOTP(totp_secret)
    login = smartapi.generateSession(
        clientCode=client_code,
        password=mpin,
        totp=totp.now(),
    )

    if not login.get("status"):
        print("Login failed:", login)
        return 1

    print("✅ Authentication successful!")
    smartapi.setAccessToken(login["data"]["jwtToken"])

    # Known-working token pairs (exchange, symbol, token)
    test_stocks = [
        ("NSE", "RELIANCE", "2885"),
        ("NSE", "TCS", "11536"),
        ("NSE", "INFY", "11536"),
        ("BSE", "500325", "500325"),
    ]

    print("Testing quotes with hardcoded tokens...")
    for exchange, symbol, token in test_stocks:
        try:
            time.sleep(0.5)  # Avoid rate limiting
            quote = smartapi.ltpData(exchange, symbol, token)
            if quote.get("status") and quote.get("data"):
                d = quote["data"]
                print(f"{symbol} ({exchange}): Rs. {d['ltp']} ({d['pChange']}%)")
                return 0
            print(f"{symbol}: Failed - {quote.get('message', 'Unknown')}")
        except Exception as e:
            print(f"{symbol}: Error - {e}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
