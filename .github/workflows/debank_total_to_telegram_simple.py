#!/usr/bin/env python3
"""
debank_total_to_telegram_simple.py
- Nessuna AccessKey richiesta
- Usa endpoint pubblico DeBank: /user/token_list (per più chain)
- Legge i secret: TELEGRAM_TOKEN e CHAT_ID (come nel tuo APY Alert)
- Invia SOLO un messaggio Telegram con Totale USD, Stable USD e % Stable

Uso rapido:
  pip install requests
  export TELEGRAM_TOKEN="..."; export CHAT_ID="..."
  python debank_total_to_telegram_simple.py --address 0x... --chains eth,arbitrum,base
"""

import os, sys, time, argparse, requests

DEBANK_PUBLIC_TOKENS_URL = "https://api.debank.com/user/token_list"
DEFAULT_CHAINS = ["eth","arbitrum","base","optimism","polygon","bsc","avalanche","fantom","linea","zksync","zkevm","scroll","sol"]

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
            time.sleep(0.2)  # throttling leggero
        except Exception as e:
            print(f"[WARN] Fetch fallito chain={ch}: {e}", file=sys.stderr)
    return total, stable_total

def send_telegram(token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text, "parse_mode":"HTML"}, timeout=30)
    r.raise_for_status()
    return r.json()

def fmt_usd(x: float) -> str:
    return f"${x:,.2f}"

def main():
    ap = argparse.ArgumentParser(description="Invia su Telegram il totale portafoglio da DeBank (pubblico).")
    ap.add_argument("--address", required=True, help="Indirizzo EVM (es. 0x...)")
    ap.add_argument("--chains", default=",".join(DEFAULT_CHAINS), help="Chain da interrogare (comma-separated)")
    args = ap.parse_args()

    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    if not token or not chat_id:
        print("ERROR: Imposta TELEGRAM_TOKEN e CHAT_ID nelle variabili d'ambiente.", file=sys.stderr)
        sys.exit(1)

    chains = [c.strip() for c in args.chains.split(",") if c.strip()]
    total, stable_total = fetch_totals_public(args.address, chains)
    pct = (stable_total/total*100) if total > 0 else 0.0

    msg = (
        f"<b>DeBank Totale Portafoglio</b>\n"
        f"Address: <code>{args.address}</code>\n"
        f"Chains: {', '.join(chains)}\n\n"
        f"Totale USD: {fmt_usd(total)}\n"
        f"Stable USD: {fmt_usd(stable_total)}  ({pct:.2f}%)"
    )
    try:
        send_telegram(token, chat_id, msg)
        print("[OK] Messaggio inviato su Telegram.")
    except Exception as e:
        print(f"[ERROR] Invio Telegram fallito: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
