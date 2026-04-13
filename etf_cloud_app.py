import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner Pro", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv"
UPDATE_INTERVAL = 600 

# --- CACHING PER VELOCITÀ ---
@st.cache_data(ttl=3600)
def get_historical_data(tickers):
    if not tickers: return None
    try: return yf.download(list(tickers), period="1y", progress=False)['Close']
    except: return None

@st.cache_data(ttl=86400)
def get_exchange_rate(from_currency):
    if from_currency == "EUR": return 1.0
    try:
        pair = f"{from_currency}EUR=X"
        rate = yf.Ticker(pair).fast_info.last_price
        return float(rate)
    except: return 1.0

# --- FUNZIONI DATI (CSV) ---
def save_data():
    if st.session_state.portfolio:
        df = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
        df.to_csv(DB_FILE, index=False)

def load_data(uploaded_file=None):
    try:
        df = pd.read_csv(uploaded_file if uploaded_file else DB_FILE)
        if not df.empty:
            st.session_state.total_budget = float(df['Total_Budget'].iloc[0])
            new_port = {}
            for _, row in df.iterrows():
                ticker = row['Ticker']; data = row.to_dict()
                del data['Ticker']; del data['Total_Budget']
                new_port[ticker] = data
            st.session_state.portfolio = new_port
    except: pass

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    if os.path.exists(DB_FILE): load_data()

if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

if 'last_update' not in st.session_state:
    st.session_state.last_update = 0.0

def sync_weight(ticker):
    st.session_state.portfolio[ticker]['Peso'] = st.session_state[f"input_w_{ticker}"]
    save_data()

# --- LOGICA PREZZI ---
def update_all_prices():
    if not st.session_state.portfolio: return
    for ticker in list(st.session_state.portfolio.keys()):
        try:
            y = yf.Ticker(ticker); i = y.info
            p = i.get('currentPrice') or i.get('regularMarketPrice')
            curr = i.get('currency', 'EUR')
            if p:
                st.session_state.portfolio[ticker]['Prezzo'] = float(p)
                st.session_state.portfolio[ticker]['Valuta'] = curr
                st.session_state.portfolio[ticker]['Cambio'] = get_exchange_rate(curr)
                st.session_state.portfolio[ticker]['Politica'] = "Dist" if (i.get('dividendYield') or 0) > 0 or "dist" in i.get('shortName','').lower() else "Acc"
        except: continue
    st.session_state.last_update = time.time()
    save_data()

if (time.time() - st.session_state.last_update) > UPDATE_INTERVAL:
    update_all_prices()

# --- CSS ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #eee; }
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 0.95rem; line-height: 1.1; }
    .ticker-label { color: #666; font-family: monospace; font-size: 0.8rem; }
    .tipo-tag { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; color: white; }
    .acc-tag { background-color: #1a73e8; }
    .dist-tag { background-color: #f29900; }
    .real-status { color: #2e7d32; font-size: 0.75rem; font-weight: 600; margin-top: 3px; }
    .just-link-btn { display: inline-block; margin-top: 5px; padding: 2px 10px; background-color: #ffffff; color: #1a73e8 !important; text-decoration: none !important; border: 1px solid #1a73e8; border-radius: 4px; font-size: 0.65rem; font-weight: 700; }
    .smart-hint { font-size: 0.72rem; color: #1a73e8; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("📊 Configurazione")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0)

with st.sidebar.expander("➕ Aggiungi ETF"):
    new_t = st.text_input("Ticker Yahoo").strip().upper()
    if st.button("Aggiungi"):
        try:
            y = yf.Ticker(new_t); i = y.info
            curr = i.get('currency', 'EUR')
            st.session_state.portfolio[new_t] = {
                'Nome': i.get('shortName', new_t), 'ISIN': i.get('underlyingSymbol') or "",
                'Politica': "Acc", 'Peso': 0.0, 'Prezzo': i.get('currentPrice') or i.get('regularMarketPrice'),
                'Valuta': curr, 'Cambio': get_exchange_rate(curr), 'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            save_data(); st.rerun()
        except: st.error("Non trovato")

st.sidebar.markdown("---")
# Tasti di Backup per GitHub
if st.sidebar.download_button("📥 Scarica Backup CSV", data=pd.DataFrame([{'Ticker': k, **v} for k, v in st.session_state.portfolio.items()]).to_csv(index=False), file_name="mio_pac.csv"):
    st.sidebar.success("File pronto!")

uploaded_file = st.sidebar.file_uploader("📤 Carica Backup", type="csv")
if uploaded_file:
    load_data(uploaded_file); st.rerun()

# --- LOGICA SMART SUGGERIMENTO ---
total_val_portafoglio = sum(a['Quote_Reali'] * a['Prezzo'] * a['Cambio'] for a in st.session_state.portfolio.values())
target_val_finale = total_val_portafoglio + st.session_state.total_budget
allocazione_smart = {}
for t, a in st.session_state.portfolio.items():
    v_ideale = target_val_finale * (a['Peso'] / 100)
    v_attuale = a['Quote_Reali'] * a['Prezzo'] * a['Cambio']
    allocazione_smart[t] = max(0, v_ideale - v_attuale)

# --- MAIN ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("Aggiungi un ETF per iniziare.")
else:
    # Tabella
    h = st.columns([2.2, 0.6, 0.7, 0.7, 0.9, 0.9, 0.7, 1.2])
    for col, text in zip(h, ["Asset", "Tipo", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Drift", "Azioni"]): col.write(f"**{text}**")

    for ticker, asset in list(st.session_state.portfolio.items()):
        p_eur = asset['Prezzo'] * asset['Cambio']
        v_attuale = asset['Quote_Reali'] * p_eur
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.2, 0.6, 0.7, 0.7, 0.9, 0.9, 0.7, 1.2])
        
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:30]}</div><div class='ticker-label'>{ticker}</div>", unsafe_allow_html=True)
            if v_attuale > 0: st.markdown(f"<div class='real-status'>Valore: {v_attuale:,.2f}€</div>", unsafe_allow_html=True)

        with c2: st.markdown(f"<br><span class='tipo-tag {'acc-tag' if asset['Politica']=='Acc' else 'dist-tag'}'>{asset['Politica']}</span>", unsafe_allow_html=True)
        c3.write(f"<br>{p_eur:,.2f}", unsafe_allow_html=True)
        c4.number_input("%", 0, 100, int(asset['Peso']), key=f"input_w_{ticker}", on_change=sync_weight, args=(ticker,), label_visibility="collapsed")
        
        target_mensile = (asset['Peso'] / 100) * st.session_state.total_budget
        target_settim = target_mensile / 4.33
        
        with c5:
            st.write(f"**{target_mensile:,.2f}**")
            st.markdown(f"<div class='smart-hint'>Smart: {allocazione_smart.get(ticker,0):,.2f}</div>", unsafe_allow_html=True)
        
        c6.write(f"{target_settim:,.2f}")
        
        with c7:
            if total_val_portafoglio > 0:
                drift = ((v_attuale / total_val_portafoglio) * 100) - asset['Peso']
                st.write(f"<br>{drift:+.1f}%", unsafe_allow_html=True)
            else: st.write("<br>-", unsafe_allow_html=True)

        with c8:
            st.write("")
            a1, a2, a3 = st.columns(3)
            if a1.button("➕", key=f"add_{ticker}", help="Aggiungi 1 settimana"):
                asset['Investito_Reale'] += target_settim
                asset['Quote_Reali'] += (target_settim / p_eur)
                save_data(); st.rerun()
            if a2.button("➖", key=f"sub_{ticker}"):
                asset['Investito_Reale'] = max(0, asset['Investito_Reale'] - target_settim)
                asset['Quote_Reali'] = max(0, asset['Quote_Reali'] - (target_settim / p_eur))
                save_data(); st.rerun()
            if a3.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; save_data(); st.rerun()

    # --- RIEPILOGO ---
    st.markdown("---")
    tot_inv = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_inv:,.2f} €")
    m2.metric("Valore Attuale", f"{total_val_portafoglio:,.2f} €")
    m3.metric("Profit/Loss", f"{total_val_portafoglio-tot_inv:,.2f} €", f"{((total_val_portafoglio/tot_inv)-1)*100 if tot_inv>0 else 0:+.2f}%")

    # --- GRAFICO ---
    try:
        tks = tuple(st.session_state.portfolio.keys())
        data = get_historical_data(tks)
        if data is not None:
            st.markdown("---")
            norm = (data / data.iloc[0]) * 100
            pesi = [st.session_state.portfolio[t]['Peso'] for t in list(data.columns)]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=norm.index, y=(norm * pesi).sum(axis=1)/100, name="IL TUO PAC", line=dict(color='red', width=3)))
            st.plotly_chart(fig, use_container_width=True)
    except: pass
