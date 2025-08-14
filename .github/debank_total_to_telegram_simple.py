#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
debank_total_to_telegram_simple.py
- No AccessKey required
- Uses DeBank public endpoint: /user/token_list across chains
- Reads secrets: TELEGRAM_TOKEN and CHAT_ID (same as your APY Alert)
- Sends ONLY a Telegram message with Total USD, Stable USD, and % Stable
"""

import os
import sys
import time
import argparse
import requests

DEBANK_PUBLIC_TOKENS_URL = "https://api.debank.com/user/token_list"
DEFAULT_CHAINS = [
    "eth", "arbitrum", "base", "optimism", "polygon",
    "bsc", "avalanche", "fantom", "linea", "zksync", "zkevm", "scroll", "sol"
]

STABLES = {
    "USDT","USDC","USDC.e","DAI","FRAX","LUSD","GUSD","TUSD","USDP","USDV","crvUSD",
    "USDe","sUSDe","USDY","PYUSD","sFRAX","USDM","OUSG","USDbC","USDT.e","USDTb","USDC.b"
}

def fetch_totals_public(address: str, chains):
    """Fetch totals from DeBank public token_list and sum USD totals and stable totals."""
    total = 0.0
    stable_total = 0.0
    headers = {"User-Agent": "Mozilla/5.0"}
    for ch in chains:
        try:
            r = requests.get(
                DEBANK_PUBLIC_TOKENS_URL,
                params={"id": address, "is_all": "true", "chain": ch},
                headers=headers, timeout=20
            )
            r.raise_for_status()
            js = r.json()
            tokens = js.get("data") or []
            for t in tokens:
                sym = (t.get("symbol") or "").strip()
                amt = float(t.get("amount") or 0)
                price = float(t.get("price") or 0)
                val = amt * price
                total += val
                if sym in STABLES:
                    stable_total += val
            time.sleep(0.2)  # light throttle to avoid rate-limits
        except Exception as e:
            print(f"[WARN] Fetch failed chain={ch}: {e}", file=sys.stderr)
    return total, stable_total

def send_telegram(token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text, "parse_mode":"HTML"}, timeout=30)
    r.raise_for_status()
    return r.json()

def fmt_usd(x: float) -> str:
    return f"${x:,.2f}"

def main():
    ap = argparse.ArgumentParser(description="Send DeBank total to Telegram (public endpoint).")
    ap.add_argument("--address", required=True, help="EVM address (e.g. 0x...)")
    ap.add_argument("--chains", default=",".join(DEFAULT_CHAINS), help="Comma-separated chains to query")
    args = ap.parse_args()

    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    if not token or not chat_id:
        print("ERROR: Set TELEGRAM_TOKEN and CHAT_ID environment variables.", file=sys.stderr)
        sys.exit(1)

    chains = [c.strip() for c in args.chains.split(",") if c.strip()]
    total, stable_total = fetch_totals_public(args.address, chains)
    pct = (stable_total / total * 100) if total > 0 else 0.0

    msg = (
        f"<b>DeBank Portfolio Total</b>\n"
        f"Address: <code>{args.address}</code>\n"
        f"Chains: {', '.join(chains)}\n\n"
        f"Total USD: {fmt_usd(total)}\n"
        f"Stable USD: {fmt_usd(stable_total)}  ({pct:.2f}%)"
    )
    try:
        send_telegram(token, chat_id, msg)
        print("[OK] Telegram message sent.")
    except Exception as e:
        print(f"[ERROR] Telegram send failed: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
