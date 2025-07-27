import requests
import csv
import datetime
import os

# CONFIG
ADDRESS = "0x6bD872Ef0749eBa102A9e7Cd9FC24Ed2A5C88679"
DEBANK_API = f"https://pro-openapi.debank.com/v1/user/total_balance?id={ADDRESS}"
CSV_FILE = "portfolio.csv"
MORPHO_THRESHOLD = 0.60  # 60%

# Legge valore CeFi manuale
try:
    with open("cefi_manual.txt") as f:
        nexo_balance = float(f.read().strip())
except FileNotFoundError:
    nexo_balance = 0.0

# Richiesta a DeBank
headers = {"accept": "application/json"}
resp = requests.get(DEBANK_API, headers=headers)
data = resp.json()

# Valore totale DeFi
total_defi = data["total_usd_value"]

# Somma CeFi manuale
total = total_defi + nexo_balance

# Breakdown protocolli principali
morpho_val = 0
beefy_val = 0
pendle_val = 0

for item in data["chain_list"]:
    for prot in item["portfolio_list"]:
        pname = prot["name"].lower()
        usd_val = prot["usd_value"]
        if "morpho" in pname or "steakhouse" in pname:
            morpho_val += usd_val
        if "beefy" in pname:
            beefy_val += usd_val
        if "pendle" in pname:
            pendle_val += usd_val

date = datetime.date.today()

row = [date, total, morpho_val, beefy_val, pendle_val, nexo_balance]

# Scrive/aggiorna CSV
file_exists = os.path.isfile(CSV_FILE)
with open(CSV_FILE, "a", newline="") as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow(["date","total","morpho","beefy","pendle","nexo"])
    writer.writerow(row)

# Controllo esposizione
if morpho_val / total > MORPHO_THRESHOLD:
    print(f"ALERT: Morpho supera il {MORPHO_THRESHOLD*100}% del portafoglio!")
else:
    print("Portafoglio OK")
