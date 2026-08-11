import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

CHANNEL = os.getenv('TELEGRAM_CHANNEL', 'share_market_news_livee').replace('@','').strip()
PUBLIC_URL = f'https://t.me/s/{CHANNEL}'
REFRESH_SECONDS = int(os.getenv('REFRESH_SECONDS', '45'))

st.set_page_config(page_title='Telegram Market Intelligence Terminal', page_icon='📡', layout='wide')

# ---------- Styling ----------
st.markdown('''
<style>
:root { --card:#111827; --muted:#94a3b8; --border:#243244; }
.block-container { padding-top: 0.8rem; padding-bottom: 2rem; max-width: 1600px; }
.header-title {font-size: 1.75rem; font-weight: 800; letter-spacing:.3px; margin:0;}
.subtle {color:#94a3b8; font-size:.88rem;}
.news-card {background:linear-gradient(135deg,#0f172a,#111827); border:1px solid #253149; border-radius:13px; padding:14px 16px; margin:9px 0;}
.news-head {display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom:7px;}
.badge {border:1px solid #334155; border-radius:999px; padding:2px 8px; font-size:.75rem; font-weight:700;}
.pos {color:#42d392; border-color:#1f7a55;} .neg {color:#ff6b6b; border-color:#923b3b;} .neu {color:#f1c75b; border-color:#806a2f;}
.high {background:#7f1d1d; color:#fecaca; border-color:#b91c1c;} .mid {background:#713f12;color:#fde68a;border-color:#a16207;} .low {background:#172554;color:#bfdbfe;border-color:#1d4ed8;}
.msg {font-size:.96rem; line-height:1.45; color:#e5e7eb; white-space:pre-wrap;}
.meta {font-size:.76rem; color:#94a3b8; margin-top:8px;}
.metric-box {border:1px solid #243244; background:#0f172a; border-radius:12px; padding:10px 12px;}
</style>
''', unsafe_allow_html=True)

POSITIVE = {
    'order win': 18, 'wins order': 18, 'bagged order': 18, 'contract': 8, 'approval': 12,
    'approved': 10, 'profit rises': 14, 'profit jumps': 16, 'strong results': 15, 'beats estimates': 16,
    'dividend': 7, 'buyback': 14, 'upgrade': 12, 'record revenue': 12, 'expansion': 8,
    'partnership': 7, 'acquisition': 7, 'fund raise': 3, 'commissioned': 10, 'launch': 5,
    'positive': 6, 'growth': 5, 'surges': 8, 'rises': 5, 'up ': 3,
}
NEGATIVE = {
    'resigns': -10, 'resignation': -10, 'downgrade': -13, 'default': -22, 'fraud': -25,
    'probe': -14, 'investigation': -14, 'penalty': -10, 'fine': -8, 'loss widens': -18,
    'profit falls': -14, 'weak results': -15, 'misses estimates': -15, 'pledge': -8,
    'sell stake': -7, 'block deal sell': -7, 'shutdown': -15, 'cancelled': -13,
    'negative': -6, 'falls': -5, 'drops': -6, 'down ': -3,
}

CATEGORY_RULES = [
    ('Results', ['results','revenue','ebitda','pat','profit','q1','q2','q3','q4','quarter']),
    ('Order Win', ['order win','wins order','bagged order','contract worth','letter of award','loa']),
    ('Regulatory', ['sebi','rbi','cerc','uperc','regulator','approval','approved','ministry','government']),
    ('Management', ['ceo','cfo','md ','managing director','resigns','resignation','appoints','appointment']),
    ('M&A', ['acquisition','acquires','merger','stake acquisition','takeover']),
    ('Fund Raising', ['qip','fund raise','fundraising','bonds','ncd','rights issue','preferential']),
    ('Promoter', ['promoter','pledge','insider','stake sale','stake purchase']),
    ('Block/Bulk Deal', ['block deal','bulk deal']),
    ('Dividend/Corporate Action', ['dividend','bonus','split','buyback','record date']),
    ('Sector/Macro', ['crude','gold','silver','rupee','usd','inflation','gdp','gift nifty','nasdaq','dow jones','policy']),
]

# Helpful aliases; the regex detector also catches explicit NSE-like tickers.
ALIASES = {
    'RELIANCE':'RELIANCE','TCS':'TCS','INFOSYS':'INFY','INFY':'INFY','HDFC BANK':'HDFCBANK','HDFCBANK':'HDFCBANK',
    'ICICI BANK':'ICICIBANK','ICICIBANK':'ICICIBANK','SBI':'SBIN','STATE BANK':'SBIN','ITC':'ITC','LT':'LT','L&T':'LT',
    'BHARTI AIRTEL':'BHARTIARTL','AIRTEL':'BHARTIARTL','BEL':'BEL','HAL':'HAL','BDL':'BDL','MAZAGON':'MAZDOCK',
    'MAZDOCK':'MAZDOCK','COCHIN SHIPYARD':'COCHINSHIP','GRSE':'GRSE','NTPC':'NTPC','POWERGRID':'POWERGRID','PFC':'PFC','REC':'RECLTD',
    'TATA MOTORS':'TATAMOTORS','TATAMOTORS':'TATAMOTORS','TATA STEEL':'TATASTEEL','JSW STEEL':'JSWSTEEL','SUN PHARMA':'SUNPHARMA',
    'CIPLA':'CIPLA','DR REDDY':'DRREDDY','DRREDDY':'DRREDDY','PIDILITE':'PIDILITIND','SUZLON':'SUZLON','HCC':'HCC',
    'ADANI POWER':'ADANIPOWER','ADANI ENTERPRISES':'ADANIENT','ADANI PORTS':'ADANIPORTS','ZOMATO':'ETERNAL','ETERNAL':'ETERNAL',
    'SWIGGY':'SWIGGY','PAYTM':'PAYTM','ONGC':'ONGC','COAL INDIA':'COALINDIA','IOC':'IOC','BPCL':'BPCL','HINDALCO':'HINDALCO',
    'VEDANTA':'VEDL','TATA POWER':'TATAPOWER','DLF':'DLF','IRCTC':'IRCTC','RVNL':'RVNL','IRFC':'IRFC','BHEL':'BHEL',
}

SECTOR_WORDS = {
    'Defence':['defence','defense','missile','army','navy','air force','aerospace'],
    'Railways':['railway','railways','metro','wagon','locomotive'],
    'Power':['power','electricity','thermal','solar','renewable','grid','transmission'],
    'Banking':['bank','lender','credit growth','deposit'],
    'IT':['software','it services','cloud','ai ','artificial intelligence','digital transformation'],
    'Pharma':['pharma','drug','usfda','fda','medicine','formulation'],
    'Metals':['steel','aluminium','aluminum','copper','zinc','metal'],
    'Oil & Gas':['crude','oil','gas','lng','refinery'],
    'Auto':['auto','vehicle','ev ','electric vehicle','car','tractor','two-wheeler'],
    'Realty':['real estate','realty','housing','property'],
}


def clean_text(s):
    return re.sub(r'\s+', ' ', (s or '')).strip()


def classify(text):
    t = text.lower()
    score = 0
    for k, v in POSITIVE.items():
        if k in t: score += v
    for k, v in NEGATIVE.items():
        if k in t: score += v

    # magnitude / materiality heuristics
    nums = re.findall(r'₹?\s*([\d,.]+)\s*(crore|cr|million|billion|%)', t)
    if nums: score += 7 if score >= 0 else -7
    if any(x in t for x in ['breaking','exclusive','board meeting','large order','major order']): score += 6

    sentiment = 'Positive' if score >= 7 else ('Negative' if score <= -7 else 'Neutral')
    impact = min(100, 42 + abs(score) * 2)
    if nums: impact += 8
    impact = min(100, impact)
    level = 'High' if impact >= 75 else ('Medium' if impact >= 58 else 'Low')

    category = 'General News'
    for cat, words in CATEGORY_RULES:
        if any(w in t for w in words):
            category = cat
            break

    stocks = []
    up = text.upper()
    for alias, sym in sorted(ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in up and sym not in stocks:
            stocks.append(sym)
    # conservative explicit ticker capture
    for token in re.findall(r'\b[A-Z][A-Z0-9&-]{2,12}\b', text):
        if token in ALIASES.values() and token not in stocks:
            stocks.append(token)

    sectors = [sector for sector, words in SECTOR_WORDS.items() if any(w in t for w in words)]
    return sentiment, int(impact), level, category, stocks[:6], sectors[:4]


@st.cache_data(ttl=30, show_spinner=False)
def fetch_public_messages(channel, limit=100):
    url = f'https://t.me/s/{channel}'
    headers = {'User-Agent':'Mozilla/5.0 (Market Intelligence Dashboard; educational use)'}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    rows = []
    for wrap in soup.select('.tgme_widget_message_wrap'):
        msg = wrap.select_one('.tgme_widget_message')
        text_el = wrap.select_one('.tgme_widget_message_text')
        time_el = wrap.select_one('time')
        if not msg or not text_el: continue
        post = msg.get('data-post','')
        msg_id = post.split('/')[-1] if '/' in post else ''
        text = clean_text(text_el.get_text(' ', strip=True))
        dt = time_el.get('datetime') if time_el else None
        link = f'https://t.me/{channel}/{msg_id}' if msg_id else f'https://t.me/{channel}'
        rows.append({'id':msg_id,'datetime':dt,'text':text,'link':link})
    # dedupe and newest first
    seen, out = set(), []
    for row in reversed(rows):
        key = row['id'] or row['text'][:120]
        if key not in seen:
            seen.add(key); out.append(row)
    return out[:limit]


def enrich(rows):
    out=[]
    for r in rows:
        sentiment, impact, level, category, stocks, sectors = classify(r['text'])
        dt = pd.to_datetime(r.get('datetime'), utc=True, errors='coerce')
        out.append({**r,'sentiment':sentiment,'impact':impact,'level':level,'category':category,
                    'stocks':stocks,'sectors':sectors,'timestamp':dt})
    return pd.DataFrame(out)


def tradingview(sym):
    return f'https://www.tradingview.com/chart/?symbol=NSE%3A{quote(sym)}'

# ---------- Header ----------
left, right = st.columns([3,1])
with left:
    st.markdown('<div class="header-title">📡 Telegram Market Intelligence Terminal</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtle">Source: @{CHANNEL} · Telegram discovery layer · rule-based impact engine</div>', unsafe_allow_html=True)
with right:
    if st.button('↻ Refresh now', use_container_width=True):
        st.cache_data.clear(); st.rerun()

# ---------- Sidebar ----------
with st.sidebar:
    st.header('Filters')
    max_messages = st.slider('Messages to scan', 20, 150, 80, 10)
    min_impact = st.slider('Minimum impact score', 0, 100, 50, 5)
    sentiment_filter = st.multiselect('Sentiment', ['Positive','Negative','Neutral'], default=['Positive','Negative','Neutral'])
    categories = ['General News'] + [x[0] for x in CATEGORY_RULES]
    category_filter = st.multiselect('Category', categories, default=[])
    stock_query = st.text_input('Stock / keyword', placeholder='e.g. BEL, order, defence')
    st.divider()
    st.caption('Trading signal warning')
    st.write('Telegram is treated as a discovery feed, not as a Buy/Sell recommendation. Verify material news with exchange/company filings.')
    st.divider()
    st.markdown(f'[Open original Telegram channel](https://t.me/{CHANNEL})')

# ---------- Fetch ----------
try:
    rows = fetch_public_messages(CHANNEL, max_messages)
    df = enrich(rows)
    fetch_error = None
except Exception as e:
    df = pd.DataFrame()
    fetch_error = str(e)

if fetch_error:
    st.error('Telegram public preview could not be read right now. The app itself is working; try Refresh or use the optional Telethon connector described in README.')
    st.code(fetch_error)
    st.stop()

if df.empty:
    st.warning('No text posts were found in the public preview. Telegram may be limiting the preview page.')
    st.stop()

# ---------- Filtering ----------
f = df[df['impact'] >= min_impact].copy()
if sentiment_filter:
    f = f[f['sentiment'].isin(sentiment_filter)]
if category_filter:
    f = f[f['category'].isin(category_filter)]
if stock_query.strip():
    q = stock_query.strip().lower()
    f = f[f.apply(lambda r: q in r['text'].lower() or q in ' '.join(r['stocks']).lower() or q in ' '.join(r['sectors']).lower(), axis=1)]

# ---------- Metrics ----------
mc = st.columns(6)
metrics = [
    ('Scanned', len(df)), ('Visible', len(f)),
    ('🟢 Positive', int((f.sentiment=='Positive').sum()) if len(f) else 0),
    ('🔴 Negative', int((f.sentiment=='Negative').sum()) if len(f) else 0),
    ('🔥 High impact', int((f.level=='High').sum()) if len(f) else 0),
    ('Stocks tagged', len(set(x for xs in f.stocks for x in xs)) if len(f) else 0),
]
for c,(label,val) in zip(mc,metrics): c.metric(label,val)

# ---------- Tabs ----------
t_live, t_stocks, t_sector, t_watch, t_raw = st.tabs(['🔥 Live Intelligence','📈 News Stocks','🧭 Sector Pulse','⭐ Watchlist','🗂 Raw Feed'])

with t_live:
    if f.empty:
        st.info('No messages match the current filters.')
    for _, r in f.sort_values(['impact','timestamp'], ascending=[False,False]).iterrows():
        senti_cls = {'Positive':'pos','Negative':'neg','Neutral':'neu'}[r.sentiment]
        level_cls = {'High':'high','Medium':'mid','Low':'low'}[r.level]
        symbols = ' · '.join(r.stocks) if r.stocks else 'MARKET'
        sectors = ' · '.join(r.sectors)
        ts = '' if pd.isna(r.timestamp) else r.timestamp.tz_convert('Asia/Kolkata').strftime('%d %b %H:%M IST')
        st.markdown(
            f'''<div class="news-card"><div class="news-head">
            <span class="badge {senti_cls}">{r.sentiment}</span>
            <span class="badge {level_cls}">{r.level} {r.impact}</span>
            <span class="badge">{r.category}</span>
            <span class="badge">{symbols}</span>
            {f'<span class="badge">{sectors}</span>' if sectors else ''}
            </div><div class="msg">{r.text}</div><div class="meta">{ts}</div></div>''', unsafe_allow_html=True)
        cols = st.columns([1.1,1.1,6])
        cols[0].link_button('Telegram ↗', r.link, use_container_width=True)
        if r.stocks:
            cols[1].link_button('Chart ↗', tradingview(r.stocks[0]), use_container_width=True)

with t_stocks:
    exploded=[]
    for _,r in f.iterrows():
        for s in r.stocks:
            exploded.append({'Stock':s,'Mentions':1,'Max Impact':r.impact,'Positive':int(r.sentiment=='Positive'),
                             'Negative':int(r.sentiment=='Negative'),'Latest':r.timestamp})
    if exploded:
        sdf=pd.DataFrame(exploded).groupby('Stock',as_index=False).agg({'Mentions':'sum','Max Impact':'max','Positive':'sum','Negative':'sum','Latest':'max'})
        sdf['Net News']=sdf['Positive']-sdf['Negative']
        sdf=sdf.sort_values(['Max Impact','Mentions'],ascending=False)
        st.dataframe(sdf, use_container_width=True, hide_index=True, column_config={
            'Max Impact': st.column_config.ProgressColumn(min_value=0,max_value=100),
            'Latest': st.column_config.DatetimeColumn(format='DD MMM HH:mm')})
        selected=st.selectbox('Open TradingView chart', sdf.Stock.tolist())
        st.link_button(f'Open {selected} on TradingView ↗', tradingview(selected))
    else:
        st.info('No stock symbols were confidently detected in the filtered messages.')

with t_sector:
    items=[]
    for _,r in f.iterrows():
        for s in r.sectors:
            items.append({'Sector':s,'Mentions':1,'Impact':r.impact,'Positive':int(r.sentiment=='Positive'),'Negative':int(r.sentiment=='Negative')})
    if items:
        sec=pd.DataFrame(items).groupby('Sector',as_index=False).agg({'Mentions':'sum','Impact':'mean','Positive':'sum','Negative':'sum'})
        sec['News Bias']=sec['Positive']-sec['Negative']
        sec['Impact']=sec['Impact'].round(0).astype(int)
        sec=sec.sort_values(['News Bias','Impact'],ascending=False)
        st.bar_chart(sec.set_index('Sector')['News Bias'])
        st.dataframe(sec, use_container_width=True, hide_index=True)
    else:
        st.info('No sector keywords detected under the current filters.')

with t_watch:
    st.write('Enter your watchlist and the terminal will show only matching Telegram news.')
    default_watch = os.getenv('DEFAULT_WATCHLIST','BEL,HAL,RELIANCE,TATAPOWER,PIDILITIND')
    wl = st.text_area('Watchlist (comma separated)', value=default_watch, height=80)
    wset={x.strip().upper() for x in wl.split(',') if x.strip()}
    if wset:
        wf=f[f.apply(lambda r: bool(wset.intersection(set(r.stocks))) or any(w.lower() in r.text.lower() for w in wset),axis=1)]
        if wf.empty: st.info('No matching watchlist news in the currently scanned messages.')
        else:
            for _,r in wf.sort_values('timestamp',ascending=False).iterrows():
                st.markdown(f'**{", ".join(r.stocks) or "Watchlist"}** · {r.sentiment} · Impact **{r.impact}**  \n{r.text}')
                st.link_button('Open Telegram ↗',r.link,key=f'w{r.id}')

with t_raw:
    raw=f[['timestamp','text','category','sentiment','impact','stocks','sectors','link']].copy()
    raw['stocks']=raw['stocks'].apply(lambda x:', '.join(x))
    raw['sectors']=raw['sectors'].apply(lambda x:', '.join(x))
    st.dataframe(raw, use_container_width=True, hide_index=True,
                 column_config={'link':st.column_config.LinkColumn('Telegram'),'impact':st.column_config.ProgressColumn(min_value=0,max_value=100)})

st.caption('Educational market-intelligence tool. Automated classification can be wrong; confirm price-sensitive information from primary sources before acting.')
