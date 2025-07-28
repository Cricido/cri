import os
import requests
from datetime import datetime
from telegram import Bot

GRAPHQL_URL = "https://api.morpho.org/graphql"
VAULT = "0xbEef047a543E45807105E51A8BBEFCc5950fcfBa"

QUERY = f"""
query {{
  vaultByAddress(address: "{VAULT}", chainId: 1) {{
    state {{
      totalAssetsUsd
      netApy
      dailyNetApy
      weeklyNetApy
      monthlyNetApy
    }}
  }}
}}
"""

def fetch_data():
    r = requests.post(GRAPHQL_URL, json={"query": QUERY})
    r.raise_for_status()
    return r.json()["data"]["vaultByAddress"]["state"]

def main():
    data = fetch_data()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    tvl = float(data["totalAssetsUsd"])
    net = float(data["netApy"]) * 100
    daily = float(data["dailyNetApy"]) * 100
    weekly = float(data["weeklyNetApy"]) * 100
    monthly = float(data["monthlyNetApy"]) * 100

    msg = (
        f"*Morpho – Steakhouse USDT*\n"
        f"`{now}`\n\n"
        f"TVL: ${tvl:,.2f}\n"
        f"Net APY: {net:.2f}%\n"
        f"Daily APY: {daily:.3f}%\n"
        f"Weekly APY: {weekly:.3f}%\n"
        f"Monthly APY: {monthly:.3f}%"
    )

    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    Bot(token=token).send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

if __name__ == "__main__":
    main()
