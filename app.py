import os, re, json, html, hashlib
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

try:
    import yfinance as yf
except Exception:
    yf = None

# ---------------- CONFIG ----------------
FEED_CHANNEL = os.getenv('MARKET_FEED_CHANNEL', 'share_market_news_livee').replace('@','').strip()
PUBLIC_URL = f'https://t.me/s/{FEED_CHANNEL}'
OPENAI_MODEL = os.getenv('OPENAI_MODEL','gpt-4.1-mini')

st.set_page_config(page_title='Market Pulse Terminal', page_icon='⚡', layout='wide', initial_sidebar_state='expanded')

# ---------------- STYLE ----------------
st.markdown('''
<style>
:root{--bg:#070b11;--panel:#0d131d;--panel2:#111a27;--line:#223047;--muted:#8090a6;--text:#edf3fb;--green:#31d18b;--red:#ff5865;--amber:#ffbf4b;--blue:#63a8ff;}
.stApp{background:var(--bg);color:var(--text)}
.block-container{max-width:1760px;padding-top:.45rem;padding-bottom:2rem}
[data-testid="stSidebar"]{background:#0a0f17;border-right:1px solid #1b2738}
[data-testid="stMetric"]{background:#0b121c;border:1px solid #1b2a3e;border-radius:9px;padding:9px 12px}
[data-testid="stMetricLabel"]{font-size:.72rem;color:#7f91a8;text-transform:uppercase;letter-spacing:.08em}
[data-testid="stMetricValue"]{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:1.42rem}
.terminal-title{font-size:1.72rem;font-weight:900;letter-spacing:.06em;margin:0;color:#f6f9ff}
.terminal-sub{font-size:.74rem;color:#6f8198;letter-spacing:.12em;text-transform:uppercase;margin-top:2px}
.top-strip{display:flex;gap:9px;overflow-x:auto;margin:9px 0 10px 0;padding-bottom:2px}
.tickerbox{min-width:155px;background:#0b121b;border:1px solid #1f2d42;border-radius:7px;padding:7px 10px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.tickername{font-size:.68rem;color:#8495aa}.tickerprice{font-size:.94rem;font-weight:800}.up{color:var(--green)}.down{color:var(--red)}.flat{color:#b5c2d2}
.section-title{font-size:.82rem;text-transform:uppercase;letter-spacing:.12em;color:#9dafc4;font-weight:800;margin:9px 0 6px}
.edge-card{background:linear-gradient(180deg,#0e1622,#0a111b);border:1px solid #213149;border-radius:10px;padding:11px 13px;margin:7px 0}
.edge-card.highpos{border-left:4px solid #31d18b}.edge-card.highneg{border-left:4px solid #ff5865}.edge-card.neutral{border-left:4px solid #59708d}
.edge-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.sym{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:1.05rem;font-weight:900;color:#fff}.co{font-size:.78rem;color:#8fa0b4}.pct{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:900}.badge{border:1px solid #2a3a52;border-radius:4px;padding:1px 6px;font-size:.65rem;text-transform:uppercase;letter-spacing:.06em;color:#b8c5d6}.badge.pos{color:#46dc99;border-color:#226d50}.badge.neg{color:#ff7480;border-color:#7a3037}.badge.res{color:#8bbcff;border-color:#315e94}.badge.hot{color:#ffd172;border-color:#80602b}
.headline{font-size:.94rem;font-weight:720;margin:6px 0 4px;line-height:1.32}.why{font-size:.77rem;color:#a4b3c6;line-height:1.35}.meta{font-size:.68rem;color:#5f7188;margin-top:5px}
.microgrid{display:grid;grid-template-columns:repeat(4,minmax(95px,1fr));gap:5px;margin-top:7px}.micro{background:#08101a;border:1px solid #18263a;border-radius:6px;padding:5px 7px}.micro .k{font-size:.60rem;color:#667991;text-transform:uppercase}.micro .v{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.84rem;font-weight:800}
.rankrow{display:grid;grid-template-columns:70px 1fr 72px;gap:8px;align-items:center;border-bottom:1px solid #152236;padding:7px 2px}.rankbar{height:5px;background:#18263a;border-radius:3px;overflow:hidden}.rankfill{height:100%;background:#4d8fda}.smallmuted{font-size:.68rem;color:#708299}
hr{border-color:#172338!important}
.stTabs [data-baseweb="tab-list"]{gap:4px;border-bottom:1px solid #1b2a3e}.stTabs [data-baseweb="tab"]{height:38px;background:#0a111a;border-radius:6px 6px 0 0;padding:0 12px;font-size:.78rem}.stTabs [aria-selected="true"]{background:#101a28!important}
</style>
''', unsafe_allow_html=True)

# ---------------- HELPERS ----------------
ALIASES = {
'TD POWER SYSTEMS':'TDPOWERSYS','TD POWER':'TDPOWERSYS','INNOVA CAPTAB':'INNOVACAP','LANDMARK CARS':'LANDMARK',
'LAXMI DENTAL':'LAXMIDENTL','DIVGI TORQTRANSFER':'DIVGIITTS','DIVGI':'DIVGIITTS','MUFIN GREEN':'MUFIN','GUJARAT ENERGY':'GIPCL',
'GUJARAT INDUSTRIAL POWER':'GIPCL','GIPCL':'GIPCL','ARIES AGRO':'ARIES','RELIANCE':'RELIANCE','TCS':'TCS','INFOSYS':'INFY','INFY':'INFY',
'HDFC BANK':'HDFCBANK','ICICI BANK':'ICICIBANK','STATE BANK':'SBIN','SBI':'SBIN','ITC':'ITC','L&T':'LT','BHARTI AIRTEL':'BHARTIARTL',
'BEL':'BEL','HAL':'HAL','BDL':'BDL','MAZAGON DOCK':'MAZDOCK','MAZDOCK':'MAZDOCK','COCHIN SHIPYARD':'COCHINSHIP','GRSE':'GRSE',
'NTPC':'NTPC','POWER GRID':'POWERGRID','POWERGRID':'POWERGRID','PFC':'PFC','REC':'RECLTD','TATA MOTORS':'TATAMOTORS','TATA STEEL':'TATASTEEL',
'JSW STEEL':'JSWSTEEL','SUN PHARMA':'SUNPHARMA','CIPLA':'CIPLA','DR REDDY':'DRREDDY','PIDILITE':'PIDILITIND','SUZLON':'SUZLON','HCC':'HCC',
'ADANI POWER':'ADANIPOWER','ADANI ENTERPRISES':'ADANIENT','ADANI PORTS':'ADANIPORTS','ETERNAL':'ETERNAL','ZOMATO':'ETERNAL','SWIGGY':'SWIGGY',
'PAYTM':'PAYTM','ONGC':'ONGC','COAL INDIA':'COALINDIA','IOC':'IOC','BPCL':'BPCL','HINDALCO':'HINDALCO','VEDANTA':'VEDL','TATA POWER':'TATAPOWER',
'DLF':'DLF','IRCTC':'IRCTC','RVNL':'RVNL','IRFC':'IRFC','BHEL':'BHEL'}

SECTOR_WORDS={'Defence':['defence','missile','aerospace','army','navy'],'Power':['power','electricity','grid','thermal','solar','renewable'],
'Railways':['railway','metro','wagon','locomotive'],'Banking':['bank','lender','credit','deposit'],'IT':['software','cloud','digital','it services'],
'Pharma':['pharma','drug','usfda','medicine'],'Metals':['steel','aluminium','copper','zinc'],'Auto':['auto','vehicle','car','tractor'],
'Oil & Gas':['oil','gas','crude','lng','refinery'],'Realty':['real estate','realty','housing']}

CAT_WORDS={
'Results':['q1fy','q2fy','q3fy','q4fy','revenue','ebitda','pat','pbt','yoy','qoq'],
'Order Win':['order win','wins order','bagged','letter of award','work order','contract worth','loa'],
'Regulatory':['approval','approved','sebi','rbi','usfda','cerc','government','ministry'],
'M&A':['acquisition','acquires','merger','takeover'],'Fund Raising':['qip','rights issue','preferential','fund raise','ncd','bonds'],
'Management':['resigns','resignation','appointed','appointment','ceo','cfo'],'Corporate Action':['dividend','bonus','split','buyback'],
'Block/Bulk Deal':['block deal','bulk deal']}
POS=['solid','strong','record','highest ever','raises guidance','guidance raised','wins','order','approval','growth','uptick','surges','margin expansion','beats']
NEG=['weak','falls','declines','downgrade','resigns','fraud','probe','penalty','loss widens','guidance cut','default','cancelled','margin contraction']


def secret(name, default=''):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)


def norm(t):
    t=(t or '').replace('\xa0',' ')
    t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n{3,}','\n\n',t)
    return t.strip()

@st.cache_data(ttl=30, show_spinner=False)
def fetch_feed(limit=60):
    r=requests.get(PUBLIC_URL,headers={'User-Agent':'Mozilla/5.0'},timeout=15); r.raise_for_status()
    soup=BeautifulSoup(r.text,'html.parser'); out=[]
    for wrap in soup.select('.tgme_widget_message_wrap'):
        msg=wrap.select_one('.tgme_widget_message'); tx=wrap.select_one('.tgme_widget_message_text'); tm=wrap.select_one('time')
        if not msg or not tx: continue
        pid=(msg.get('data-post','').split('/')[-1] or '')
        out.append({'id':pid,'text':norm(tx.get_text('\n',strip=True)),'datetime':tm.get('datetime') if tm else None})
    return list(reversed(out))[:limit]


def num(s):
    try:return float(str(s).replace(',',''))
    except:return None


def metrics_from_text(text):
    t=text.replace('₹',''); out={}
    aliases={'Revenue':['rev','revenue','sales'],'EBITDA':['ebitda'],'PBT':['pbt'],'PAT':['pat','net profit']}
    for k,als in aliases.items():
        a='|'.join(map(re.escape,als))
        m=re.search(rf'(?i)\b(?:{a})\b[^\d]{{0,20}}([\d,.]+)\s*(?:cr|crore)?\s*(?:vs|v)\s*([\d,.]+)',t)
        if m:
            cur,prev=num(m.group(1)),num(m.group(2)); delta=((cur/prev-1)*100 if cur is not None and prev not in (None,0) else None)
            out[k]={'current':cur,'previous':prev,'change_pct':round(delta,1) if delta is not None else None}
    return out


def fallback_split(text):
    text=norm(text).replace('\n',' ')
    # Main pattern: company name immediately followed by hashtag. Keep each company block intact.
    pat=re.compile(r'(?=(?:^|\s)([A-Z][A-Za-z0-9&.()/\-]*(?:\s+[A-Z][A-Za-z0-9&.()/\-]*){0,5})\s+(#[A-Za-z][A-Za-z0-9_]{2,}))')
    matches=list(pat.finditer(text)); chunks=[]
    if matches:
        starts=[m.start(1) for m in matches]
        # remove nested/near duplicate starts
        clean=[]
        for s in starts:
            if not clean or s-clean[-1]>12: clean.append(s)
        starts=clean+[len(text)]
        for a,b in zip(starts,starts[1:]):
            c=text[a:b].strip(' ,;|-')
            if len(c)>18: chunks.append(c)
    if not chunks:
        # line/sentence fallback
        chunks=[x.strip() for x in re.split(r'(?<=[.!?])\s+(?=[A-Z#])',text) if len(x.strip())>20]
    return chunks or [text]


def infer_company_ticker(text):
    m=re.match(r'^\s*([A-Za-z][A-Za-z0-9&.()/\- ]{1,60}?)\s+(?=#\w+)',text)
    company=m.group(1).strip() if m else ''
    tags=re.findall(r'#([A-Za-z][A-Za-z0-9_]{2,})',text)
    up=text.upper()
    ticker=''
    for a,s in sorted(ALIASES.items(),key=lambda x:-len(x[0])):
        if re.search(r'(?<![A-Z0-9])'+re.escape(a)+r'(?![A-Z0-9])',up):
            ticker=s; company=company or a.title(); break
    if not ticker and tags:
        # common finance hashtags are not tickers
        skip={'Q1FY27','Q2FY27','Q3FY27','Q4FY27','RESULTS','STOCKMARKET','NIFTY'}
        for tag in tags:
            if tag.upper() not in skip and len(tag)<=18:
                ticker=tag.upper(); break
    if not company:
        company=ticker or 'Market Update'
    return company,ticker


def classify_fallback(text):
    lo=' '+text.lower()+' '
    cat='Market News'
    for k,words in CAT_WORDS.items():
        if any(w in lo for w in words):cat=k;break
    score=sum(1 for w in POS if w in lo)-sum(1 for w in NEG if w in lo)
    ms=metrics_from_text(text)
    deltas=[v['change_pct'] for v in ms.values() if v.get('change_pct') is not None]
    if deltas: score += sum(1 for d in deltas if d>8)-sum(1 for d in deltas if d<-8)
    sent='Positive' if score>=1 else ('Negative' if score<=-1 else 'Neutral')
    impact=min(98,52+abs(score)*7+(12 if cat in ['Results','Order Win','Regulatory','M&A'] else 0))
    company,ticker=infer_company_ticker(text)
    sectors=[s for s,ws in SECTOR_WORDS.items() if any(w in lo for w in ws)]
    headline=re.sub(r'\s+',' ',text)[:210]
    why='Material corporate update. Check price reaction and whether the event changes earnings, order book or risk.'
    if cat=='Results' and deltas:
        best=max(deltas,key=abs); why=f'Reported result shows a {abs(best):.1f}% {"improvement" if best>0 else "decline"} in a key extracted metric; price confirmation matters.'
    elif cat=='Order Win': why='Fresh order/contract catalyst. Its value should be compared with annual revenue and existing order book.'
    elif cat=='Regulatory': why='Regulatory development may affect earnings or execution; materiality depends on scope and timeline.'
    return {'company':company,'ticker':ticker,'category':cat,'sentiment':sent,'impact':impact,'headline':headline,'why_it_matters':why,'sector':sectors[0] if sectors else 'Other','metrics':ms}


def ai_extract(text):
    key=secret('OPENAI_API_KEY','')
    if not key: return None
    system='''You are a financial-news normalization engine for Indian equities. Convert a raw market-news digest into separate company-level events. Never invent facts. Identify the most likely NSE ticker only when confident; otherwise use empty string. Return ONLY valid JSON with key events, an array. Each event: company, ticker, category (Results|Order Win|Regulatory|M&A|Fund Raising|Management|Corporate Action|Block/Bulk Deal|Market News), sentiment (Positive|Negative|Neutral), impact integer 0-100, headline <= 26 words, why_it_matters <= 34 words, sector, metrics object. metrics may contain Revenue, EBITDA, PBT, PAT, OrderValue; each metric object can include current, previous, change_pct. Split multi-company digests carefully. Ignore promotional boilerplate.'''
    payload={'model':OPENAI_MODEL,'messages':[{'role':'system','content':system},{'role':'user','content':text[:14000]}], 'temperature':0.1,'response_format':{'type':'json_object'}}
    try:
        r=requests.post('https://api.openai.com/v1/chat/completions',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json=payload,timeout=40)
        r.raise_for_status(); content=r.json()['choices'][0]['message']['content']; obj=json.loads(content)
        ev=obj.get('events',[]) if isinstance(obj,dict) else []
        return ev if isinstance(ev,list) else None
    except Exception:
        return None

@st.cache_data(ttl=600, show_spinner=False)
def enrich(rows, use_ai=True):
    events=[]
    for r in rows:
        parsed=ai_extract(r['text']) if use_ai else None
        if parsed:
            pieces=parsed
        else:
            pieces=[]
            for c in fallback_split(r['text']): pieces.append(classify_fallback(c))
        for i,e in enumerate(pieces):
            if not isinstance(e,dict): continue
            ticker=(e.get('ticker') or '').upper().strip().replace('.NS','')
            company=(e.get('company') or ticker or 'Market Update').strip()
            # normalize metric shape
            mets=e.get('metrics') if isinstance(e.get('metrics'),dict) else {}
            events.append({'event_id':f"{r['id']}-{i}",'timestamp':pd.to_datetime(r['datetime'],utc=True,errors='coerce'),
                           'company':company,'ticker':ticker,'category':e.get('category','Market News'),'sentiment':e.get('sentiment','Neutral'),
                           'impact':int(max(0,min(100,e.get('impact',50) or 50))),'headline':e.get('headline','') or company,
                           'why':e.get('why_it_matters','') or 'Material update; assess price response and earnings relevance.',
                           'sector':e.get('sector','Other') or 'Other','metrics':mets})
    return pd.DataFrame(events)

@st.cache_data(ttl=120, show_spinner=False)
def quote_batch(tickers):
    result={}
    clean=sorted({t for t in tickers if t and re.fullmatch(r'[A-Z0-9&\-]{1,20}',t)})
    if not clean or yf is None:return result
    syms=[t+'.NS' for t in clean]
    try:
        data=yf.download(syms,period='5d',interval='1d',group_by='ticker',auto_adjust=False,progress=False,threads=True)
        for t,s in zip(clean,syms):
            try:
                if len(syms)==1:
                    close=data['Close'].dropna()
                else:
                    close=data[s]['Close'].dropna()
                if len(close)>=1:
                    last=float(close.iloc[-1]); prev=float(close.iloc[-2]) if len(close)>=2 else last
                    pct=(last/prev-1)*100 if prev else 0
                    result[t]={'price':last,'change_pct':pct}
            except Exception: pass
    except Exception: pass
    return result


def tv(t): return f'https://www.tradingview.com/chart/?symbol=NSE%3A{quote(t)}'

def fmt_num(v):
    try:return f'{float(v):,.1f}'
    except:return '—'

def metric_html(metrics):
    blocks=[]
    for k in ['Revenue','EBITDA','PBT','PAT','OrderValue']:
        v=metrics.get(k)
        if not isinstance(v,dict):continue
        cur=v.get('current'); ch=v.get('change_pct')
        if cur is None and ch is None: continue
        val=(f'₹{fmt_num(cur)} Cr' if cur is not None else '')
        if ch is not None: val += f' <span class="{"up" if float(ch)>=0 else "down"}">{float(ch):+.1f}%</span>'
        blocks.append(f'<div class="micro"><div class="k">{html.escape(k)}</div><div class="v">{val}</div></div>')
    return '<div class="microgrid">'+''.join(blocks[:4])+'</div>' if blocks else ''

# ---------------- DATA ----------------
with st.sidebar:
    st.markdown('### CONTROL PANEL')
    posts_n=st.slider('News depth',20,100,50,10)
    min_imp=st.slider('Minimum impact',0,100,55,5)
    cats=st.multiselect('Event type',list(CAT_WORDS.keys())+['Market News'],default=[])
    sentiments=st.multiselect('Bias',['Positive','Negative','Neutral'],default=['Positive','Negative','Neutral'])
    query=st.text_input('Find stock / company',placeholder='BEL, TD Power, Reliance')
    st.divider()
    st.caption('SMART PARSING')
    ai_available=bool(secret('OPENAI_API_KEY',''))
    use_ai=st.toggle('AI event extraction',value=ai_available,disabled=not ai_available)
    st.caption('AI mode improves company/ticker extraction from mixed multi-company digests.' if ai_available else 'Rules mode active. Add OPENAI_API_KEY in Streamlit Secrets to enable AI parsing.')
    if st.button('↻ Refresh data',use_container_width=True): st.cache_data.clear(); st.rerun()

try:
    rows=fetch_feed(posts_n)
    df=enrich(rows,use_ai=use_ai)
except Exception as e:
    st.error('Market news feed is temporarily unavailable.'); st.code(str(e)); st.stop()
if df.empty:
    st.warning('No market events were extracted.'); st.stop()

quotes=quote_batch(df.ticker.tolist())
df['price']=df.ticker.map(lambda x:quotes.get(x,{}).get('price'))
df['change_pct']=df.ticker.map(lambda x:quotes.get(x,{}).get('change_pct'))

f=df[df.impact>=min_imp].copy()
if cats:f=f[f.category.isin(cats)]
if sentiments:f=f[f.sentiment.isin(sentiments)]
if query.strip():
    q=query.lower().strip(); f=f[f.apply(lambda r:q in str(r.company).lower() or q in str(r.ticker).lower() or q in str(r.headline).lower(),axis=1)]

# ---------------- HEADER ----------------
a,b=st.columns([5,1])
with a:
    st.markdown('<div class="terminal-title">MARKET PULSE <span style="color:#5789c8">//</span> NEWS INTELLIGENCE</div>',unsafe_allow_html=True)
    st.markdown('<div class="terminal-sub">Indian equities · event-ranked · price-aware</div>',unsafe_allow_html=True)
with b:
    mode='AI PARSING' if use_ai else 'RULE PARSING'
    st.markdown(f'<div style="text-align:right;padding-top:7px;font-family:monospace;color:#7f93ad;font-size:.75rem">{mode}<br>LIVE FEED</div>',unsafe_allow_html=True)

# Market strip: indices + top news stocks
index_quotes={}
if yf is not None:
    try:
        ix=yf.download(['^NSEI','^NSEBANK'],period='5d',interval='1d',group_by='ticker',auto_adjust=False,progress=False,threads=True)
        for lab,sym in [('NIFTY 50','^NSEI'),('BANK NIFTY','^NSEBANK')]:
            c=ix[sym]['Close'].dropna(); last=float(c.iloc[-1]); prev=float(c.iloc[-2]); index_quotes[lab]=(last,(last/prev-1)*100)
    except Exception: pass
strip=[]
for lab,(p,ch) in index_quotes.items():strip.append((lab,p,ch))
news_tickers=f.dropna(subset=['change_pct']).sort_values('impact',ascending=False).ticker.drop_duplicates().tolist()[:5]
for t in news_tickers:
    qv=quotes.get(t,{}); strip.append((t,qv.get('price'),qv.get('change_pct')))
if strip:
    h='<div class="top-strip">'
    for lab,p,ch in strip:
        cls='up' if (ch or 0)>0 else ('down' if (ch or 0)<0 else 'flat')
        h+=f'<div class="tickerbox"><div class="tickername">{html.escape(lab)}</div><div class="tickerprice">{fmt_num(p)} <span class="{cls}">{(ch or 0):+.2f}%</span></div></div>'
    h+='</div>'; st.markdown(h,unsafe_allow_html=True)

# KPIs
k1,k2,k3,k4,k5=st.columns(5)
k1.metric('High impact',int((f.impact>=75).sum()))
k2.metric('Positive',int((f.sentiment=='Positive').sum()))
k3.metric('Negative',int((f.sentiment=='Negative').sum()))
k4.metric('Stocks in focus',f[f.ticker!=''].ticker.nunique())
k5.metric('Results',int((f.category=='Results').sum()))

# ---------------- TABS ----------------
tabs=st.tabs(['⚡ LIVE EDGE','🧾 RESULTS','🚀 CATALYSTS','◫ SECTOR FLOW','★ WATCHLIST','▦ ALL EVENTS'])

with tabs[0]:
    left,right=st.columns([2.45,1],gap='large')
    with left:
        st.markdown('<div class="section-title">Priority event stream</div>',unsafe_allow_html=True)
        show=f.sort_values(['impact','timestamp'],ascending=[False,False]).head(28)
        if show.empty: st.info('No events match the current filters.')
        for _,r in show.iterrows():
            ch=r.change_pct; cls='up' if pd.notna(ch) and ch>0 else ('down' if pd.notna(ch) and ch<0 else 'flat')
            edge='highpos' if r.sentiment=='Positive' else ('highneg' if r.sentiment=='Negative' else 'neutral')
            sym=r.ticker or '—'; price=f'₹{r.price:,.2f}' if pd.notna(r.price) else 'Price n/a'; pct=f'{ch:+.2f}%' if pd.notna(ch) else '—'
            ts='' if pd.isna(r.timestamp) else r.timestamp.tz_convert('Asia/Kolkata').strftime('%H:%M · %d %b')
            st.markdown(f'''<div class="edge-card {edge}"><div class="edge-top"><span class="sym">{html.escape(sym)}</span><span class="co">{html.escape(r.company)}</span><span class="pct {cls}">{price} &nbsp; {pct}</span><span class="badge {"pos" if r.sentiment=="Positive" else "neg" if r.sentiment=="Negative" else ""}">{r.sentiment}</span><span class="badge res">{html.escape(r.category)}</span><span class="badge hot">IMPACT {int(r.impact)}</span></div><div class="headline">{html.escape(str(r.headline))}</div><div class="why">{html.escape(str(r.why))}</div>{metric_html(r.metrics)}<div class="meta">{ts} IST · {html.escape(str(r.sector))}</div></div>''',unsafe_allow_html=True)
            if r.ticker: st.link_button('Open chart ↗',tv(r.ticker),key='live'+r.event_id)
    with right:
        st.markdown('<div class="section-title">News stocks · ranked</div>',unsafe_allow_html=True)
        rank=[]
        for t,g in f[f.ticker!=''].groupby('ticker'):
            qv=quotes.get(t,{})
            rank.append({'ticker':t,'company':g.iloc[0].company,'mentions':len(g),'impact':int(g.impact.max()),'bias':int((g.sentiment=='Positive').sum()-(g.sentiment=='Negative').sum()),'change':qv.get('change_pct')})
        rank=sorted(rank,key=lambda x:(x['impact'],x['mentions']),reverse=True)[:14]
        for x in rank:
            ch=x['change']; ccls='up' if ch is not None and ch>0 else ('down' if ch is not None and ch<0 else 'flat')
            width=max(8,min(100,x['impact']))
            st.markdown(f'''<div class="rankrow"><div><b style="font-family:monospace">{x['ticker']}</b><div class="smallmuted">{x['mentions']} event(s)</div></div><div><div class="rankbar"><div class="rankfill" style="width:{width}%"></div></div><div class="smallmuted">impact {x['impact']} · bias {x['bias']:+d}</div></div><div class="{ccls}" style="font-family:monospace;text-align:right;font-weight:800">{ch:+.2f}%</div></div>''' if ch is not None else f'''<div class="rankrow"><div><b style="font-family:monospace">{x['ticker']}</b><div class="smallmuted">{x['mentions']} event(s)</div></div><div><div class="rankbar"><div class="rankfill" style="width:{width}%"></div></div><div class="smallmuted">impact {x['impact']} · bias {x['bias']:+d}</div></div><div class="flat" style="text-align:right">—</div></div>''',unsafe_allow_html=True)

with tabs[1]:
    st.markdown('<div class="section-title">Result surprise board</div>',unsafe_allow_html=True)
    rd=f[f.category=='Results'].copy(); rec=[]
    for _,r in rd.iterrows():
        row={'Stock':r.ticker,'Company':r.company,'Price':r.price,'% Chg':r.change_pct,'Impact':r.impact,'Bias':r.sentiment,'Headline':r.headline}
        for m in ['Revenue','EBITDA','PBT','PAT']:
            x=r.metrics.get(m,{}) if isinstance(r.metrics,dict) else {}
            row[m+' Δ%']=x.get('change_pct') if isinstance(x,dict) else None
        rec.append(row)
    if rec:
        rr=pd.DataFrame(rec).sort_values(['Impact','PAT Δ%'],ascending=[False,False])
        st.dataframe(rr,use_container_width=True,hide_index=True,column_config={'Price':st.column_config.NumberColumn(format='₹ %.2f'),'% Chg':st.column_config.NumberColumn(format='%.2f%%'),'Impact':st.column_config.ProgressColumn(min_value=0,max_value=100),'Revenue Δ%':st.column_config.NumberColumn(format='%.1f%%'),'EBITDA Δ%':st.column_config.NumberColumn(format='%.1f%%'),'PBT Δ%':st.column_config.NumberColumn(format='%.1f%%'),'PAT Δ%':st.column_config.NumberColumn(format='%.1f%%')})
    else:st.info('No result events under current filters.')

with tabs[2]:
    st.markdown('<div class="section-title">Corporate catalyst radar</div>',unsafe_allow_html=True)
    cd=f[f.category!='Results'].sort_values(['impact','timestamp'],ascending=[False,False]).head(40)
    if cd.empty:st.info('No catalysts under current filters.')
    else:
        table=cd[['ticker','company','category','sentiment','impact','price','change_pct','headline','sector']].copy()
        table.columns=['Stock','Company','Event','Bias','Impact','Price','% Chg','What happened','Sector']
        st.dataframe(table,use_container_width=True,hide_index=True,column_config={'Impact':st.column_config.ProgressColumn(min_value=0,max_value=100),'Price':st.column_config.NumberColumn(format='₹ %.2f'),'% Chg':st.column_config.NumberColumn(format='%.2f%%')})

with tabs[3]:
    st.markdown('<div class="section-title">Sector news pressure</div>',unsafe_allow_html=True)
    sec=[]
    for s,g in f.groupby('sector'):
        if s=='Other':continue
        sec.append({'Sector':s,'Events':len(g),'Positive':int((g.sentiment=='Positive').sum()),'Negative':int((g.sentiment=='Negative').sum()),'Avg Impact':round(g.impact.mean(),1),'Pressure':int((g.sentiment=='Positive').sum()-(g.sentiment=='Negative').sum())})
    if sec:
        sdf=pd.DataFrame(sec).sort_values(['Pressure','Avg Impact'],ascending=False)
        st.bar_chart(sdf.set_index('Sector')['Pressure']); st.dataframe(sdf,use_container_width=True,hide_index=True)
    else:st.info('Not enough sector-tagged events yet.')

with tabs[4]:
    wl=st.text_input('Watchlist (comma separated)',value=secret('DEFAULT_WATCHLIST','BEL,HAL,RELIANCE,TATAPOWER,PIDILITIND'))
    w={x.strip().upper() for x in wl.split(',') if x.strip()}
    wf=f[f.apply(lambda r:r.ticker in w or any(x in r.company.upper() for x in w),axis=1)] if w else f.iloc[:0]
    if wf.empty:st.info('No current events match the watchlist.')
    else:
        for _,r in wf.sort_values(['impact','timestamp'],ascending=[False,False]).iterrows():
            ch=r.change_pct; ccls='up' if pd.notna(ch) and ch>0 else ('down' if pd.notna(ch) and ch<0 else 'flat')
            st.markdown(f'<div class="edge-card"><div class="edge-top"><span class="sym">{r.ticker or "—"}</span><span class="co">{html.escape(r.company)}</span><span class="pct {ccls}">{ch:+.2f}%</span><span class="badge res">{r.category}</span><span class="badge hot">{r.impact}</span></div><div class="headline">{html.escape(str(r.headline))}</div><div class="why">{html.escape(str(r.why))}</div></div>' if pd.notna(ch) else f'<div class="edge-card"><div class="edge-top"><span class="sym">{r.ticker or "—"}</span><span class="co">{html.escape(r.company)}</span><span class="badge res">{r.category}</span><span class="badge hot">{r.impact}</span></div><div class="headline">{html.escape(str(r.headline))}</div><div class="why">{html.escape(str(r.why))}</div></div>',unsafe_allow_html=True)
            if r.ticker:st.link_button('Open chart ↗',tv(r.ticker),key='wl'+r.event_id)

with tabs[5]:
    allv=f[['timestamp','ticker','company','category','sentiment','impact','price','change_pct','headline','sector']].copy()
    allv.columns=['Time','Stock','Company','Event','Bias','Impact','Price','% Chg','Headline','Sector']
    st.dataframe(allv.sort_values('Time',ascending=False),use_container_width=True,hide_index=True,column_config={'Time':st.column_config.DatetimeColumn(format='DD MMM HH:mm'),'Impact':st.column_config.ProgressColumn(min_value=0,max_value=100),'Price':st.column_config.NumberColumn(format='₹ %.2f'),'% Chg':st.column_config.NumberColumn(format='%.2f%%')})

st.markdown('<div class="smallmuted" style="margin-top:14px">Market-intelligence dashboard. Price-sensitive information should be cross-checked with exchange/company disclosures before execution.</div>',unsafe_allow_html=True)
