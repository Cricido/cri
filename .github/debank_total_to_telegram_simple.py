#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeBank → Telegram
- 1) Tenta Pro API: /v1/user/total_balance  (include posizioni in protocollo: Morpho, Pendle, ecc.)
- 2) Fallback: public /user/all_token_list (e se serve /user/token_list chain-by-chain) -> può non includere posizioni in protocollo
- Invia SOLO un messaggio Telegram con Total USD; stima Stable USD dal fallback
Env richieste:
  TELEGRAM_TOKEN, CHAT_ID
  (opzionale) DEBANK_ACCESS_KEY
"""

import os, sys, time, argparse, requests
from typing import List, Tuple

PRO_TOTAL_URL     = "https://pro-openapi.debank.com/v1/user/total_balance"
ALL_TOKEN_URL     = "https://api.debank.com/user/all_token_list"
TOKEN_LIST_URL    = "https://api.debank.com/user/token_list"

DEFAULT_CHAINS = [
    "eth","arbitrum","base","optimism","polygon",
    "bsc","avalanche","fantom","linea","zksync","zkevm","scroll","sol"
]

STABLES = {
    "USDT","USDC","USDC.e","DAI","FRAX","LUSD","GUSD","TUSD","USDP","USDV","crvUSD",
    "USDe","sUSDe","USDY","PYUSD","sFRAX","USDM","OUSG","USDbC","USDT.e","USDTb","USDC.b"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://debank.com",
    "Referer": "https://debank.com/",
}

def pro_total(address: str, access_key: str):
    if not access_key:
        return None
    try:
        r = requests.get(
            PRO_TOTAL_URL,
            params={"id": address},
            headers={"accept": "application/json", "AccessKey": access_key},
            timeout=20
        )
        r.raise_for_status()
        js = r.json()
        return float(js.get("total_usd_value") or 0.0)
    except Exception as e:
        print(f"[WARN] Pro API total_balance fallita: {e}", file=sys.stderr)
        return None

def fetch_all_token_list(address: str):
    try:
        r = requests.get(ALL_TOKEN_URL, params={"id": address, "is_all": "true"}, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json().get("data") or []
    except Exception as e:
        print(f"[WARN] all_token_list fallita: {e}", file=sys.stderr)
        return []

def fetch_token_list_chain(address: str, chain: str):
    try:
        r = requests.get(TOKEN_LIST_URL, params={"id": address, "is_all": "true", "chain": chain},
                         headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json().get("data") or []
    except Exception as e:
        print(f"[WARN] token_list {chain} fallita: {e}", file=sys.stderr)
        return []

def accumulate(tokens) -> Tuple[float, float, int]:
    total = stable = 0.0
    cnt = 0
    for t in tokens:
        try:
            sym = (t.get("symbol") or "").strip()
            amt = float(t.get("amount") or 0)
            price = float(t.get("price") or 0)
            val = amt * price
            total += val
            if sym in STABLES:
                stable += val
            cnt += 1
        except Exception:
            continue
    return total, stable, cnt

def fallback_totals(address: str, chains: List[str]) -> Tuple[float, float, int]:
    tokens = fetch_all_token_list(address)
    if tokens:
        return accumulate(tokens)
    grand = []
    for ch in chains:
        t = fetch_token_list_chain(address, ch)
        grand.extend(t)
        time.sleep(0.2)
    return accumulate(grand)

def send_telegram(token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text, "parse_mode":"HTML"}, timeout=30)
    r.raise_for_status()
    return r.json()

def fmt_usd(x: float) -> str:
    return f"${x:,.2f}"

def main():
    ap = argparse.ArgumentParser(description="DeBank total → Telegram (include protocol via Pro API se disponibile).")
    ap.add_argument("--address", required=True, help="EVM address (0x...)")
    ap.add_argument("--chains", default=",".join(DEFAULT_CHAINS), help="Fallback chains (comma-separated)")
    args = ap.parse_args()

    tg_token = os.getenv("TELEGRAM_TOKEN")
    chat_id  = os.getenv("CHAT_ID")
    if not tg_token or not chat_id:
        print("ERROR: set TELEGRAM_TOKEN e CHAT_ID.", file=sys.stderr)
        sys.exit(1)

    access_key = os.getenv("DEBANK_ACCESS_KEY", "")
    chains = [c.strip() for c in args.chains.split(",") if c.strip()]

    # 1) Totale “vero” via Pro API (include Morpho/Pendle)
    total = pro_total(args.address, access_key)

    # 2) Fallback pubblico per stimare stable e (se manca Pro) avere un totale
    fb_total, fb_stable, fb_cnt = fallback_totals(args.address, chains)
    if total is None:
        total = fb_total  # meno accurato: non include posizioni in protocollo

    pct = (fb_stable / total * 100) if (total and total > 0) else 0.0

    msg = (
        f"<b>DeBank Portfolio Total</b>\n"
        f"Address: <code>{args.address}</code>\n"
        f"Chains (fallback): {', '.join(chains)}\n\n"
        f"Total USD: {fmt_usd(total)}\n"
        f"Stable (fallback) USD: {fmt_usd(fb_stable)}  ({pct:.2f}%)"
    )
    if not access_key:
        msg += ("\n\n⚠️ <i>Senza DEBANK_ACCESS_KEY, le posizioni in protocollo (Morpho/Pendle) potrebbero non essere nel totale.</i>")

    try:
        send_telegram(tg_token, chat_id, msg)
        print("[OK] Telegram inviato.")
    except Exception as e:
        print(f"[ERROR] Invio Telegram fallito: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
