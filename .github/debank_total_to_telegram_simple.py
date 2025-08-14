#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeBank → Telegram (public endpoints)
- 1) Tenta /user/all_token_list (tutte le chain in un colpo)
- 2) Fallback: /user/token_list per ciascuna chain
- Somma Total USD + Stable USD e invia SOLO un messaggio Telegram
- Secrets richiesti: TELEGRAM_TOKEN, CHAT_ID
"""

import os
import sys
import time
import argparse
import requests
from typing import List, Tuple

ALL_TOKEN_URL   = "https://api.debank.com/user/all_token_list"
TOKEN_LIST_URL  = "https://api.debank.com/user/token_list"

DEFAULT_CHAINS = [
    "eth","arbitrum","base","optimism","polygon",
    "bsc","avalanche","fantom","linea","zksync","zkevm","scroll","sol"
]

# Elenco di stable/peg USD (aggiungi/rimuovi se vuoi)
STABLES = {
    "USDT","USDC","USDC.e","DAI","FRAX","LUSD","GUSD","TUSD","USDP","USDV","crvUSD",
    "USDe","sUSDe","USDY","PYUSD","sFRAX","USDM","OUSG","USDbC","USDT.e","USDTb","USDC.b"
}

HEADERS = {
    # header "realistici" per evitare blocchi
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                  " AppleWebKit/537.36 (KHTML, like Gecko)"
                  " Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://debank.com",
    "Referer": "https://debank.com/",
}

def fetch_all_token_list(address: str, retries: int = 3, sleep_s: float = 0.8):
    """Tenta l'endpoint 'all_token_list' (più affidabile)."""
    params = {"id": address, "is_all": "true"}
    for i in range(retries):
        try:
            r = requests.get(ALL_TOKEN_URL, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            js = r.json()
            tokens = js.get("data") or []
            return tokens
        except Exception as e:
            print(f"[WARN] all_token_list tentativo {i+1}/{retries} fallito: {e}", file=sys.stderr)
            time.sleep(sleep_s * (i+1))
    return []

def fetch_token_list_chain(address: str, chain: str, retries: int = 2, sleep_s: float = 0.6):
    """Fallback: token_list per singola chain."""
    params = {"id": address, "is_all": "true", "chain": chain}
    for i in range(retries):
        try:
            r = requests.get(TOKEN_LIST_URL, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            js = r.json()
            tokens = js.get("data") or []
            return tokens
        except Exception as e:
            print(f"[WARN] token_list {chain} tentativo {i+1}/{retries} fallito: {e}", file=sys.stderr)
            time.sleep(sleep_s * (i+1))
    return []

def accumulate_values(tokens) -> Tuple[float, float, int]:
    """Somma totale USD e stable USD da una lista di token 'data' DeBank."""
    total = 0.0
    stable_total = 0.0
    count = 0
    for t in tokens:
        try:
            sym   = (t.get("symbol") or "").strip()
            amt   = float(t.get("amount") or 0)
            price = float(t.get("price") or 0)
            val   = amt * price
            total += val
            if sym in STABLES:
                stable_total += val
            count += 1
        except Exception:
            # salta token malformati
            continue
    return total, stable_total, count

def fetch_totals(address: str, chains: List[str]) -> Tuple[float, float, int]:
    """Prova all_token_list, se vuoto fallback a token_list per chain."""
    # 1) all_token_list
    tokens = fetch_all_token_list(address)
    if tokens:
        total, stable_total, count = accumulate_values(tokens)
        print(f"[INFO] all_token_list: {count} token", flush=True)
        return total, stable_total, count

    # 2) fallback per chain
    grand = []
    for ch in chains:
        tks = fetch_token_list_chain(address, ch)
        print(f"[INFO] {ch}: {len(tks)} token", flush=True)
        grand.extend(tks)
        time.sleep(0.2)
    total, stable_total, count = accumulate_values(grand)
    return total, stable_total, count

def send_telegram(token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text, "parse_mode":"HTML"}, timeout=30)
    r.raise_for_status()
    return r.json()

def fmt_usd(x: float) -> str:
    return f"${x:,.2f}"

def main():
    ap = argparse.ArgumentParser(description="Invia su Telegram il totale portafoglio (DeBank public endpoints).")
    ap.add_argument("--address", required=True, help="Indirizzo EVM (0x...)")
    ap.add_argument("--chains", default=",".join(DEFAULT_CHAINS), help="Chain fallback, comma-separated")
    args = ap.parse_args()

    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    if not token or not chat_id:
        print("ERROR: imposta TELEGRAM_TOKEN e CHAT_ID come secrets/variabili d'ambiente.", file=sys.stderr)
        sys.exit(1)

    chains = [c.strip() for c in args.chains.split(",") if c.strip()]
    total, stable_total, count = fetch_totals(args.address, chains)
    pct = (stable_total / total * 100) if total > 0 else 0.0

    # Messaggio
    msg = (
        f"<b>DeBank Portfolio Total</b>\n"
        f"Address: <code>{args.address}</code>\n"
        f"Chains: {', '.join(chains)}\n\n"
        f"Total USD: {fmt_usd(total)}\n"
        f"Stable USD: {fmt_usd(stable_total)}  ({pct:.2f}%)"
    )
    if count == 0:
        msg += (
            "\n\n⚠️ <i>Nessun token trovato dagli endpoint pubblici.</i>"
            "\nSuggerimenti: riduci le chain, riprova più tardi (rate-limit),"
            " oppure usa la Pro API (AccessKey) per un totale affidabile."
        )

    try:
        send_telegram(token, chat_id, msg)
        print("[OK] Telegram inviato.")
    except Exception as e:
        print(f"[ERROR] Invio Telegram fallito: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
