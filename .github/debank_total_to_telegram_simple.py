name: DeBank Total → Telegram

on:
  schedule:
    - cron: '0 6 * * *'   # 08:00 CEST (UTC+2)
    - cron: '0 12 * * *'  # 14:00 CEST (UTC+2)
  workflow_dispatch:

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r .github/requirements_telegram.txt
      - name: Send DeBank totals to Telegram
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          CHAT_ID: ${{ secrets.CHAT_ID }}
        run: |
          python .github/debank_total_to_telegram_simple.py \
            --address 0x6bD872Ef0749eBa102A9e7Cd9FC24Ed2A5C88679 \
            --chains eth,arbitrum,base,optimism,polygon
