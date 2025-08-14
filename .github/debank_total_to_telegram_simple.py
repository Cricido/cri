#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import argparse
import requests

DEBANK_PUBLIC_TOKENS_URL = "https://api.debank.com/user/token_list"
DEFAULT_CHAINS = ["eth","arbitrum","base","optimism","polygon","bsc","avalanche"]

STABLES = {
    "USDT","USDC","USDC.e","DAI","FRAX","LUSD","GUSD","TUSD","USDP","USDV","crvUSD",
    "USDe","sUSDe","USDY","PYUSD","sFRAX","USDM","OUSG","USDbC","USDT.e","USDTb","USDC.b"
}

def fetch_totals_public(address: str, chains):
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
            time.sleep(0.2)
        except Exception as e:
