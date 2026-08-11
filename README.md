# Telegram Market Intelligence Terminal — V2

This Streamlit app converts the public Telegram channel `@share_market_news_livee` into structured market events.

## What V2 fixes
The first version could treat a long Telegram results digest as one huge message. V2 preserves Telegram line breaks and also splits long digest messages before `Company Name #Ticker` markers. Each extracted event is then scored/classified separately.

## Main views
- **Action Board** — highest-impact individual events with a plain-English “what matters” takeaway.
- **Results Radar** — extracts Revenue / EBITDA / PBT / PAT and approximate comparison % where the Telegram text uses `current vs previous` figures.
- **Catalysts** — order wins, regulatory events, M&A, fund raising, management/promoter/corporate actions.
- **Stock News Score** — ranks stocks/companies by repeated positive/negative catalysts and max impact.
- **Sector Pulse** — sector-level news bias.
- **Watchlist** — only events that match your stocks/company keywords.
- **Raw Events** — the decomposed event stream for debugging/verification.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Environment variables (optional)
```text
TELEGRAM_CHANNEL=share_market_news_livee
REFRESH_SECONDS=45
DEFAULT_WATCHLIST=BEL,HAL,RELIANCE,TATAPOWER,PIDILITIND
```

## Important limitation
The public Telegram web preview is convenient but not a guaranteed API. For a production terminal, use a Telegram user-client connector (for example Telethon) and keep `api_id` / `api_hash` in Streamlit secrets or environment variables, never in GitHub.

The classification and financial metric extraction are heuristic. Treat Telegram as the discovery/speed layer and verify price-sensitive information from NSE/BSE/company filings before acting.
