# Market Pulse Terminal V3

A Streamlit market-news intelligence dashboard for Indian equities.

## What changed in V3
- Feed source is entirely background-only; no source branding or source links appear in the UI.
- Company/ticker-first event cards.
- Latest stock price and 1-session % change via Yahoo Finance/yfinance.
- Optional AI extraction for dense multi-company result/news digests.
- Results surprise board, catalyst radar, sector pressure, watchlist and ranked news stocks.
- Direct TradingView chart button.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Enable AI parsing on Streamlit Community Cloud
Open your app -> Manage app -> Settings -> Secrets and add:
```toml
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
OPENAI_MODEL = "gpt-4.1-mini"
```
Then reboot the app. If no API key is supplied, V3 automatically uses the built-in deterministic parser.

## GitHub replacement
Upload/replace `app.py`, `requirements.txt`, `.gitignore`, `README.md`, and optionally `.streamlit/secrets.toml.example`.
Do not upload an actual `secrets.toml` containing your API key.
