# Telegram Market Intelligence Terminal

A Streamlit dashboard that turns posts from a public Telegram market-news channel into a filtered intelligence feed.

Default channel: `@share_market_news_livee`

## Features
- Reads Telegram public web preview (no API key required for v1)
- Positive / Negative / Neutral tagging
- Impact score (0–100)
- News categories: results, order wins, regulatory, management, M&A, fund raising, promoter, block/bulk deals, corporate actions, macro/sector
- NSE stock symbol tagging for common Indian names
- Sector pulse
- Watchlist-only news
- TradingView chart buttons
- Original Telegram post links
- Filters for impact, category, sentiment and keywords

## Run locally

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud
1. Upload these files to a GitHub repository.
2. In Streamlit Community Cloud choose **New app**.
3. Select the repository and `app.py`.
4. Deploy.

No Telegram credential is required for the public-preview mode.

## Configuration
Copy `.env.example` to `.env` for local use, or configure environment variables in your host:

- `TELEGRAM_CHANNEL=share_market_news_livee`
- `REFRESH_SECONDS=45`
- `DEFAULT_WATCHLIST=BEL,HAL,RELIANCE,TATAPOWER,PIDILITIND`

## Important limitation
Public Telegram preview HTML is convenient but not a guaranteed API contract. Telegram can throttle it or change its markup. For a production/commercial terminal, use Telegram's official API authorization with your own `api_id` and `api_hash` and a client such as Telethon. Telegram documents the creation of API credentials under **API development tools**. Never commit API credentials or session files to GitHub.

## Suggested production upgrade
The next version should add:
1. Telethon ingestion (reliable message history + new-message stream)
2. NSE/BSE corporate-announcement verification
3. Better company/entity master for Nifty 500 symbols
4. Duplicate-news clustering
5. Live price/volume/relative-strength confirmation
6. Persistent database (SQLite/Postgres)
7. Alerts for high-impact watchlist news

## Disclaimer
This dashboard is for information/education. Telegram content and automated sentiment/impact classification may be incomplete or incorrect. Verify material news from primary exchange/company sources before making a trading decision.
