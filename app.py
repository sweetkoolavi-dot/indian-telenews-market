import os
import re
import html
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

CHANNEL = os.getenv('TELEGRAM_CHANNEL', 'share_market_news_livee').replace('@', '').strip()
REFRESH_SECONDS = int(os.getenv('REFRESH_SECONDS', '45'))
PUBLIC_URL = f'https://t.me/s/{CHANNEL}'

st.set_page_config(page_title='Telegram Market Intelligence Terminal', page_icon='📡', layout='wide')

st.markdown('''
<style>
.block-container {padding-top:.65rem; padding-bottom:2rem; max-width:1650px}
.header-title{font-size:1.75rem;font-weight:850;letter-spacing:.2px;margin:0}
.subtle{color:#94a3b8;font-size:.88rem}
.news-card{background:linear-gradient(135deg,#0f172a,#111827);border:1px solid #263348;border-radius:14px;padding:13px 15px;margin:8px 0}
.news-head{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
.badge{border:1px solid #334155;border-radius:999px;padding:2px 8px;font-size:.74rem;font-weight:750}
.pos{color:#42d392;border-color:#1f7a55}.neg{color:#ff6b6b;border-color:#923b3b}.neu{color:#f1c75b;border-color:#806a2f}
.high{background:#7f1d1d;color:#fecaca;border-color:#b91c1c}.mid{background:#713f12;color:#fde68a;border-color:#a16207}.low{background:#172554;color:#bfdbfe;border-color:#1d4ed8}
.msg{font-size:.96rem;line-height:1.42;color:#e5e7eb}.meta{font-size:.75rem;color:#94a3b8;margin-top:6px}
.callout{background:#0b1220;border:1px solid #273449;border-radius:12px;padding:10px 12px;margin:5px 0 10px 0;color:#cbd5e1}
.small{font-size:.80rem;color:#94a3b8}
</style>
''', unsafe_allow_html=True)

# ------------------ Rules ------------------
POSITIVE = {
    'order win':18,'wins order':18,'bagged order':18,'letter of award':18,'loa':12,'contract worth':14,
    'approval':10,'approved':9,'profit rises':14,'profit jumps':16,'strong':8,'beats':12,'record':9,
    'margin expansion':10,'highest ever':13,'guidance raised':14,'raises revenue guidance':15,'upgrade':11,
    'dividend':6,'buyback':13,'commissioned':9,'growth':5,'uptick':5,'improves':6,'rises':4,'surges':7,
}
NEGATIVE = {
    'resigns':-10,'resignation':-10,'downgrade':-13,'default':-22,'fraud':-25,'probe':-14,'investigation':-14,
    'penalty':-10,'loss widens':-18,'profit falls':-14,'weak':-8,'misses':-12,'pledge':-8,'shutdown':-15,
    'cancelled':-13,'guidance cut':-15,'margin contraction':-10,'declines':-5,'falls':-5,'drops':-6,
}
CATEGORY_RULES = [
    ('Results',['results','revenue',' rev ','ebitda','pat','pbt','q1fy','q2fy','q3fy','q4fy','yoy','qoq']),
    ('Order Win',['order win','wins order','bagged order','contract worth','letter of award',' loa ','work order']),
    ('Regulatory',['sebi','rbi','cerc','uperc','regulator','approval','approved','ministry','government','usfda','fda']),
    ('Management',[' ceo ',' cfo ',' md ','managing director','resigns','resignation','appoints','appointment']),
    ('M&A',['acquisition','acquires','merger','stake acquisition','takeover']),
    ('Fund Raising',['qip','fund raise','fundraising','bonds','ncd','rights issue','preferential']),
    ('Promoter',['promoter','pledge','insider','stake sale','stake purchase']),
    ('Block/Bulk Deal',['block deal','bulk deal']),
    ('Corporate Action',['dividend','bonus','split','buyback','record date']),
    ('Sector/Macro',['crude','gold','silver','rupee','usd','inflation','gdp','gift nifty','nasdaq','dow jones','policy']),
]
ALIASES = {
    'RELIANCE':'RELIANCE','TCS':'TCS','INFOSYS':'INFY','INFY':'INFY','HDFC BANK':'HDFCBANK','HDFCBANK':'HDFCBANK',
    'ICICI BANK':'ICICIBANK','ICICIBANK':'ICICIBANK','SBI':'SBIN','STATE BANK':'SBIN','ITC':'ITC','L&T':'LT',
    'BHARTI AIRTEL':'BHARTIARTL','AIRTEL':'BHARTIARTL','BEL':'BEL','HAL':'HAL','BDL':'BDL','MAZAGON':'MAZDOCK',
    'MAZDOCK':'MAZDOCK','COCHIN SHIPYARD':'COCHINSHIP','GRSE':'GRSE','NTPC':'NTPC','POWERGRID':'POWERGRID','PFC':'PFC','REC':'RECLTD',
    'TATA MOTORS':'TATAMOTORS','TATA STEEL':'TATASTEEL','JSW STEEL':'JSWSTEEL','SUN PHARMA':'SUNPHARMA','CIPLA':'CIPLA',
    'DR REDDY':'DRREDDY','PIDILITE':'PIDILITIND','SUZLON':'SUZLON','HCC':'HCC','ADANI POWER':'ADANIPOWER',
    'ADANI ENTERPRISES':'ADANIENT','ADANI PORTS':'ADANIPORTS','ZOMATO':'ETERNAL','ETERNAL':'ETERNAL','SWIGGY':'SWIGGY',
    'PAYTM':'PAYTM','ONGC':'ONGC','COAL INDIA':'COALINDIA','IOC':'IOC','BPCL':'BPCL','HINDALCO':'HINDALCO','VEDANTA':'VEDL',
    'TATA POWER':'TATAPOWER','DLF':'DLF','IRCTC':'IRCTC','RVNL':'RVNL','IRFC':'IRFC','BHEL':'BHEL','TD POWER':'TDPOWERSYS',
    'GUJARAT INDUSTRIAL POWER':'GIPCL','GIPCL':'GIPCL','LANDMARK CARS':'LANDMARK','DIVGI':'DIVGIITTS','LAXMI DENTAL':'LAXMIDENTL',
}
SECTOR_WORDS = {
    'Defence':['defence','defense','missile','army','navy','air force','aerospace'],
    'Railways':['railway','railways','metro','wagon','locomotive'],
    'Power':['power','electricity','thermal','solar','renewable','grid','transmission'],
    'Banking':['bank','lender','credit growth','deposit'],
    'IT':['software','it services','cloud','artificial intelligence','digital transformation'],
    'Pharma':['pharma','drug','usfda','fda','medicine','formulation'],
    'Metals':['steel','aluminium','aluminum','copper','zinc','metal'],
    'Oil & Gas':['crude','oil','gas','lng','refinery'],
    'Auto':['auto','vehicle','electric vehicle','car','tractor','two-wheeler'],
    'Realty':['real estate','realty','housing','property'],
}

# ------------------ Text parsing ------------------
def normalize_text(s):
    if not s: return ''
    s = s.replace('\xa0',' ')
    s = re.sub(r'[ \t]+',' ',s)
    s = re.sub(r'\n{3,}','\n\n',s)
    return s.strip()

COMPANY_HASHTAG_START = re.compile(
    r'(?=(?:^|\s)([A-Z][A-Za-z0-9&.()\-/]{1,}(?:\s+[A-Z][A-Za-z0-9&.()\-/]{1,}){0,5})\s+(#(?:[A-Za-z][A-Za-z0-9_]{2,})))'
)

def split_digest(text):
    """Convert one Telegram digest into individual stock/news events."""
    text = normalize_text(text)
    if not text: return []

    # 1) Telegram paragraph/line boundaries are the strongest signal.
    lines = [x.strip(' •·|–—-\t') for x in re.split(r'\n+', text) if x.strip()]
    chunks = []
    for line in lines:
        if len(line) <= 650:
            chunks.append(line)
            continue
        # 2) Many market channels make one huge results digest. Split before "Company Name #Ticker".
        starts = [m.start(1) for m in COMPANY_HASHTAG_START.finditer(line)]
        starts = sorted(set(starts))
        if len(starts) >= 2:
            if starts[0] > 15:
                starts = [0] + starts
            starts.append(len(line))
            for a,b in zip(starts, starts[1:]):
                piece=line[a:b].strip(' ,;|-')
                if len(piece) >= 20: chunks.append(piece)
        else:
            # 3) Last resort: sentence groupings, never show a 3,000-char card.
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z#])', line)
            buf=''
            for s in sentences:
                if len(buf)+len(s) > 520 and buf:
                    chunks.append(buf.strip()); buf=s
                else: buf=(buf+' '+s).strip()
            if buf: chunks.append(buf)

    # Second pass: even short lines can contain multiple "Company #Ticker" segments.
    out=[]
    for c in chunks:
        starts=[m.start(1) for m in COMPANY_HASHTAG_START.finditer(c)]
        starts=sorted(set(starts))
        if len(starts)>=2:
            if starts[0] > 12: starts=[0]+starts
            starts.append(len(c))
            out.extend([c[a:b].strip(' ,;|-') for a,b in zip(starts,starts[1:]) if len(c[a:b].strip())>=20])
        else:
            out.append(c)

    # drop navigation boilerplate + duplicates
    seen=set(); cleaned=[]
    for c in out:
        c=re.sub(r'\s+',' ',c).strip()
        if len(c)<18: continue
        if c.lower() in {'view in telegram','open in telegram'}: continue
        key=re.sub(r'\W+','',c.lower())[:160]
        if key not in seen:
            seen.add(key); cleaned.append(c)
    return cleaned or [re.sub(r'\s+',' ',text)]


def extract_company(text):
    # Company text preceding the first hashtag is usually the cleanest label in market digests.
    m=re.search(r'^\s*([A-Za-z][A-Za-z0-9&.()\-/ ]{1,55}?)\s+(?=#\w+)',text)
    if m:
        return re.sub(r'\s+',' ',m.group(1)).strip(' -|')
    up=text.upper()
    for alias in sorted(ALIASES,key=len,reverse=True):
        if re.search(r'\b'+re.escape(alias)+r'\b',up): return alias.title()
    tag=re.search(r'#([A-Za-z][A-Za-z0-9_]{2,})',text)
    return tag.group(1) if tag else 'Market'


def detect_stocks(text):
    stocks=[]; up=text.upper()
    for alias,sym in sorted(ALIASES.items(),key=lambda x:-len(x[0])):
        if re.search(r'(?<![A-Z0-9])'+re.escape(alias)+r'(?![A-Z0-9])',up) and sym not in stocks:
            stocks.append(sym)
    # explicit cash-market ticker style hashtag where known alias value
    for tag in re.findall(r'#([A-Za-z][A-Za-z0-9_]{2,})',text):
        tu=tag.upper()
        if tu in ALIASES.values() and tu not in stocks: stocks.append(tu)
    return stocks[:5]


def parse_number(s):
    try:return float(str(s).replace(',',''))
    except:return None


def extract_metrics(text):
    """Extract common result/order numbers. Values are heuristic, for radar—not accounting-grade parsing."""
    t=text.replace('₹','')
    metric_aliases={
        'Revenue':['rev','revenue','sales'], 'EBITDA':['ebitda'], 'PBT':['pbt'], 'PAT':['pat','net profit']
    }
    result={}
    for metric,aliases in metric_aliases.items():
        alias='|'.join(re.escape(a) for a in aliases)
        # e.g. Rev at 640cr vs 371cr, Q4 at 589cr
        m=re.search(rf'(?i)\b(?:{alias})\b[^\d]{{0,18}}([\d,.]+)\s*(?:cr|crore)?\s*(?:vs|v)\s*([\d,.]+)\s*(?:cr|crore)?',t)
        if m:
            cur,prev=parse_number(m.group(1)),parse_number(m.group(2))
            if cur is not None and prev not in (None,0):
                result[metric]=(cur,prev,round((cur/prev-1)*100,1))
        else:
            m=re.search(rf'(?i)\b(?:{alias})\b[^\d]{{0,18}}(?:at\s*)?([\d,.]+)\s*(?:cr|crore)',t)
            if m: result[metric]=(parse_number(m.group(1)),None,None)
    # biggest rupee/crore amount is often order value in an order announcement
    amounts=[]
    for m in re.finditer(r'(?i)(?:₹\s*)?([\d,.]+)\s*(cr|crore)',text):
        v=parse_number(m.group(1))
        if v is not None: amounts.append(v)
    if amounts: result['Largest ₹Cr']=max(amounts)
    return result


def classify(text):
    t=' '+text.lower()+' '
    raw=0
    for k,v in POSITIVE.items():
        if k in t: raw+=v
    for k,v in NEGATIVE.items():
        if k in t: raw+=v

    metrics=extract_metrics(text)
    # numerical result direction is more useful than words like "solid"
    deltas=[v[2] for k,v in metrics.items() if isinstance(v,tuple) and v[2] is not None]
    if deltas:
        pos=sum(1 for d in deltas if d>=8); neg=sum(1 for d in deltas if d<=-8)
        raw += 7*pos - 7*neg
        if len(deltas)>=2 and pos==len(deltas): raw+=8
        if len(deltas)>=2 and neg==len(deltas): raw-=8

    category='General News'
    for cat,words in CATEGORY_RULES:
        if any(w in t for w in words): category=cat; break

    material=0
    if metrics: material+=7
    if category in {'Order Win','Results','Regulatory','M&A'}: material+=7
    if any(x in t for x in ['guidance','order book','highest ever','record','large order','major order']): material+=6
    impact=min(100,max(30,43+abs(raw)*1.7+material))
    sentiment='Positive' if raw>=7 else ('Negative' if raw<=-7 else 'Neutral')
    level='High' if impact>=75 else ('Medium' if impact>=58 else 'Low')
    stocks=detect_stocks(text)
    sectors=[s for s,words in SECTOR_WORDS.items() if any(w in t for w in words)]
    return sentiment,int(impact),level,category,stocks,sectors[:4],metrics


def build_takeaway(row):
    cat=row['category']; sent=row['sentiment']; m=row['metrics']
    if cat=='Results':
        deltas=[]
        for k,v in m.items():
            if isinstance(v,tuple) and v[2] is not None: deltas.append((k,v[2]))
        if deltas:
            strongest=max(deltas,key=lambda x:abs(x[1]))
            direction='improved' if strongest[1]>0 else 'declined'
            return f"{strongest[0]} {direction} {abs(strongest[1]):.1f}% vs comparison period. Check whether price/volume confirms the result reaction."
        return 'Result-related event detected. Compare reported growth, margins and management guidance before acting.'
    if cat=='Order Win':
        amt=m.get('Largest ₹Cr')
        return f"Order catalyst detected{f' (~₹{amt:,.0f} Cr mentioned)' if amt else ''}. Judge materiality against company revenue/order book."
    if cat=='Regulatory': return 'Regulatory event: verify the primary filing/order and assess financial impact and implementation timeline.'
    if cat=='Management': return 'Management event: distinguish routine succession from unexpected key-person departure.'
    if cat=='M&A': return 'M&A event: focus on deal size, funding, valuation and earnings accretion/dilution.'
    if sent=='Positive': return 'Positive catalyst detected; use price/volume confirmation rather than headline direction alone.'
    if sent=='Negative': return 'Negative catalyst detected; watch for gap-down/volume response and any company clarification.'
    return 'Informational event; no strong directional edge detected from the text alone.'


def tradingview(sym): return f'https://www.tradingview.com/chart/?symbol=NSE%3A{quote(sym)}'

@st.cache_data(ttl=30,show_spinner=False)
def fetch_public_messages(channel,limit=100):
    url=f'https://t.me/s/{channel}'
    r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=15); r.raise_for_status()
    soup=BeautifulSoup(r.text,'html.parser'); rows=[]
    for wrap in soup.select('.tgme_widget_message_wrap'):
        msg=wrap.select_one('.tgme_widget_message'); text_el=wrap.select_one('.tgme_widget_message_text'); time_el=wrap.select_one('time')
        if not msg or not text_el: continue
        post=msg.get('data-post',''); msg_id=post.split('/')[-1] if '/' in post else ''
        # IMPORTANT: preserve line breaks. They often separate individual market events.
        text=normalize_text(text_el.get_text('\n',strip=True))
        dt=time_el.get('datetime') if time_el else None
        link=f'https://t.me/{channel}/{msg_id}' if msg_id else f'https://t.me/{channel}'
        rows.append({'id':msg_id,'datetime':dt,'text':text,'link':link})
    seen=set(); out=[]
    for row in reversed(rows):
        key=row['id'] or row['text'][:120]
        if key not in seen: seen.add(key); out.append(row)
    return out[:limit]


def enrich_messages(rows):
    events=[]
    for r in rows:
        atoms=split_digest(r['text'])
        for i,text in enumerate(atoms):
            sentiment,impact,level,category,stocks,sectors,metrics=classify(text)
            events.append({
                'event_id':f"{r['id']}-{i}",'parent_id':r['id'],'datetime':r['datetime'],'timestamp':pd.to_datetime(r['datetime'],utc=True,errors='coerce'),
                'text':text,'link':r['link'],'company':extract_company(text),'sentiment':sentiment,'impact':impact,'level':level,
                'category':category,'stocks':stocks,'sectors':sectors,'metrics':metrics,
            })
    return pd.DataFrame(events)

# ------------------ Header ------------------
left,right=st.columns([3,1])
with left:
    st.markdown('<div class="header-title">📡 Telegram Market Intelligence Terminal</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="subtle">@{CHANNEL} → event splitter → stock/category parser → catalyst radar</div>',unsafe_allow_html=True)
with right:
    if st.button('↻ Refresh now',use_container_width=True): st.cache_data.clear(); st.rerun()

with st.sidebar:
    st.header('Scan & Filter')
    max_messages=st.slider('Telegram posts to scan',20,150,80,10)
    min_impact=st.slider('Minimum impact',0,100,45,5)
    sentiment_filter=st.multiselect('Sentiment',['Positive','Negative','Neutral'],default=['Positive','Negative','Neutral'])
    category_filter=st.multiselect('Category',[x[0] for x in CATEGORY_RULES]+['General News'],default=[])
    stock_query=st.text_input('Stock / company / keyword',placeholder='BEL, TD Power, order, defence')
    st.divider()
    st.caption('What changed in V2')
    st.write('A long Telegram digest is split into individual company events before scoring. The dashboard ranks catalysts instead of displaying the raw post as one card.')
    st.markdown(f'[Open Telegram channel](https://t.me/{CHANNEL})')

try:
    raw_rows=fetch_public_messages(CHANNEL,max_messages)
    df=enrich_messages(raw_rows); fetch_error=None
except Exception as e:
    df=pd.DataFrame(); fetch_error=str(e)

if fetch_error:
    st.error('Telegram preview could not be read right now. Try Refresh. For production reliability, use the Telethon connector described in README.')
    st.code(fetch_error); st.stop()
if df.empty:
    st.warning('No usable text events were detected.'); st.stop()

f=df[df.impact>=min_impact].copy()
if sentiment_filter: f=f[f.sentiment.isin(sentiment_filter)]
if category_filter: f=f[f.category.isin(category_filter)]
if stock_query.strip():
    q=stock_query.lower().strip()
    f=f[f.apply(lambda r:q in r.text.lower() or q in r.company.lower() or q in ' '.join(r.stocks).lower() or q in ' '.join(r.sectors).lower(),axis=1)]

# KPIs
mcols=st.columns(7)
vals=[('Posts',len(raw_rows)),('Events extracted',len(df)),('Visible',len(f)),('🟢 Positive',int((f.sentiment=='Positive').sum())),('🔴 Negative',int((f.sentiment=='Negative').sum())),('🔥 High',int((f.level=='High').sum())),('Stocks tagged',len(set(x for xs in f.stocks for x in xs)))]
for c,(lab,v) in zip(mcols,vals): c.metric(lab,v)

st.markdown('<div class="callout"><b>Terminal logic:</b> Telegram is the speed/discovery layer. Each digest is decomposed into company-level events, ranked for materiality, and converted into a “what matters” takeaway. It still requires exchange/company verification before a trade.</div>',unsafe_allow_html=True)

TAB=st.tabs(['⚡ Action Board','🧾 Results Radar','🚀 Catalysts','📈 Stock News Score','🧭 Sector Pulse','⭐ Watchlist','🗂 Raw Events'])

with TAB[0]:
    st.subheader('Highest-value events now')
    af=f.sort_values(['impact','timestamp'],ascending=[False,False]).head(30)
    if af.empty: st.info('No events match the filters.')
    for _,r in af.iterrows():
        senti_cls={'Positive':'pos','Negative':'neg','Neutral':'neu'}[r.sentiment]; lvl={'High':'high','Medium':'mid','Low':'low'}[r.level]
        ts='' if pd.isna(r.timestamp) else r.timestamp.tz_convert('Asia/Kolkata').strftime('%d %b %H:%M')
        stock=' · '.join(r.stocks) if r.stocks else r.company
        safe=html.escape(r.text[:700]); takeaway=html.escape(build_takeaway(r))
        st.markdown(f'''<div class="news-card"><div class="news-head"><span class="badge {senti_cls}">{r.sentiment}</span><span class="badge {lvl}">{r.level} {r.impact}</span><span class="badge">{html.escape(r.category)}</span><span class="badge">{html.escape(stock)}</span></div><div class="msg"><b>{html.escape(r.company)}</b> — {safe}</div><div class="small">💡 {takeaway}</div><div class="meta">{ts} IST</div></div>''',unsafe_allow_html=True)
        c1,c2,c3=st.columns([1,1,6]); c1.link_button('Telegram ↗',r.link,key=f"tg{r.event_id}",use_container_width=True)
        if r.stocks: c2.link_button('Chart ↗',tradingview(r.stocks[0]),key=f"tv{r.event_id}",use_container_width=True)

with TAB[1]:
    rdf=f[f.category=='Results'].copy()
    records=[]
    for _,r in rdf.iterrows():
        rec={'Company':r.company,'Stock':r.stocks[0] if r.stocks else '','Bias':r.sentiment,'Impact':r.impact,'Time':r.timestamp,'Telegram':r.link}
        for metric in ['Revenue','EBITDA','PBT','PAT']:
            v=r.metrics.get(metric)
            rec[metric]=v[0] if isinstance(v,tuple) else None
            rec[metric+' Δ%']=v[2] if isinstance(v,tuple) else None
        records.append(rec)
    if records:
        rr=pd.DataFrame(records).sort_values(['Impact','PAT Δ%','EBITDA Δ%'],ascending=[False,False,False])
        st.dataframe(rr,use_container_width=True,hide_index=True,column_config={
            'Impact':st.column_config.ProgressColumn(min_value=0,max_value=100),
            'Telegram':st.column_config.LinkColumn('Source'),
            'Time':st.column_config.DatetimeColumn(format='DD MMM HH:mm'),
            'Revenue Δ%':st.column_config.NumberColumn(format='%.1f%%'),'EBITDA Δ%':st.column_config.NumberColumn(format='%.1f%%'),'PBT Δ%':st.column_config.NumberColumn(format='%.1f%%'),'PAT Δ%':st.column_config.NumberColumn(format='%.1f%%')})
        st.caption('Δ% is extracted heuristically from “current vs previous” numbers in the Telegram text. Confirm against the filing/result sheet.')
    else: st.info('No result events under current filters.')

with TAB[2]:
    cats=['Order Win','Regulatory','M&A','Fund Raising','Management','Promoter','Corporate Action','Block/Bulk Deal']
    cf=f[f.category.isin(cats)].sort_values(['impact','timestamp'],ascending=[False,False])
    if cf.empty: st.info('No corporate catalysts under current filters.')
    else:
        for _,r in cf.iterrows():
            st.markdown(f"**{r.company}** · {r.category} · **{r.sentiment}** · Impact **{r.impact}**  \n{r.text}  \n💡 {build_takeaway(r)}")
            st.link_button('Source ↗',r.link,key=f"cat{r.event_id}")

with TAB[3]:
    items=[]
    for _,r in f.iterrows():
        names=r.stocks or ([r.company] if r.company!='Market' else [])
        for s in names:
            items.append({'Stock / Company':s,'Mentions':1,'Positive':int(r.sentiment=='Positive'),'Negative':int(r.sentiment=='Negative'),'Neutral':int(r.sentiment=='Neutral'),'Impact':r.impact,'Latest':r.timestamp})
    if items:
        sdf=pd.DataFrame(items).groupby('Stock / Company',as_index=False).agg({'Mentions':'sum','Positive':'sum','Negative':'sum','Neutral':'sum','Impact':'max','Latest':'max'})
        sdf['News Score']=((sdf.Positive-sdf.Negative)*12+sdf.Impact).clip(0,100)
        sdf=sdf.sort_values(['News Score','Impact','Mentions'],ascending=False)
        st.dataframe(sdf,use_container_width=True,hide_index=True,column_config={'Impact':st.column_config.ProgressColumn(min_value=0,max_value=100),'News Score':st.column_config.ProgressColumn(min_value=0,max_value=100),'Latest':st.column_config.DatetimeColumn(format='DD MMM HH:mm')})
        st.caption('News Score ranks repeated positive/negative catalysts; it is not a Buy/Sell score.')
    else: st.info('No stock/company labels detected.')

with TAB[4]:
    items=[]
    for _,r in f.iterrows():
        for s in r.sectors: items.append({'Sector':s,'Mentions':1,'Positive':int(r.sentiment=='Positive'),'Negative':int(r.sentiment=='Negative'),'Impact':r.impact})
    if items:
        sec=pd.DataFrame(items).groupby('Sector',as_index=False).agg({'Mentions':'sum','Positive':'sum','Negative':'sum','Impact':'mean'})
        sec['Bias']=sec.Positive-sec.Negative; sec['Impact']=sec.Impact.round().astype(int); sec=sec.sort_values(['Bias','Impact'],ascending=False)
        st.bar_chart(sec.set_index('Sector')['Bias']); st.dataframe(sec,use_container_width=True,hide_index=True)
    else: st.info('No sectors detected.')

with TAB[5]:
    default_watch=os.getenv('DEFAULT_WATCHLIST','BEL,HAL,RELIANCE,TATAPOWER,PIDILITIND')
    wl=st.text_area('Watchlist — ticker or company keyword, comma separated',value=default_watch,height=75)
    wset={x.strip().upper() for x in wl.split(',') if x.strip()}
    wf=f[f.apply(lambda r:any(w in r.text.upper() or w in r.company.upper() or w in r.stocks for w in wset),axis=1)] if wset else f.iloc[0:0]
    if wf.empty: st.info('No current event matches the watchlist.')
    else:
        for _,r in wf.sort_values(['impact','timestamp'],ascending=[False,False]).iterrows():
            st.markdown(f"**{r.company}** · {r.category} · {r.sentiment} · Impact **{r.impact}**  \n{r.text}  \n💡 {build_takeaway(r)}")
            st.link_button('Telegram ↗',r.link,key=f"wl{r.event_id}")

with TAB[6]:
    raw=f[['timestamp','parent_id','company','text','category','sentiment','impact','stocks','sectors','link']].copy()
    raw['stocks']=raw.stocks.apply(lambda x:', '.join(x)); raw['sectors']=raw.sectors.apply(lambda x:', '.join(x))
    st.dataframe(raw,use_container_width=True,hide_index=True,column_config={'link':st.column_config.LinkColumn('Telegram'),'impact':st.column_config.ProgressColumn(min_value=0,max_value=100),'timestamp':st.column_config.DatetimeColumn(format='DD MMM HH:mm')})

st.caption('Educational market-intelligence tool. Telegram may contain errors, rumours or delayed information. Verify price-sensitive information with exchange/company filings.')
