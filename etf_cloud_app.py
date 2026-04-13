import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import urllib.parse
import re
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner Pro", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv"

# --- CSS ESTETICA ---
st.markdown("""
    <style>
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 1.1rem; }
    .isin-display { color: #d32f2f; font-weight: bold; font-family: monospace; font-size: 0.9rem; margin-bottom: 5px; }
    .real-status { color: #666; font-size: 0.8rem; font-style: italic; }
    .search-container { background-color: #f0f7ff; padding: 15px; border-radius: 10px; border: 1px solid #1a73e8; margin-bottom: 20px; }
    .just-link-btn { 
        display: inline-block; margin-top: 8px; padding: 6px 18px; 
        background-color: #ffffff; color: #1a73e8 !important; 
        text-decoration: none !important; border: 1px solid #1a73e8;
        border-radius: 20px; font-size: 0.75rem; font-weight: 700; 
        text-transform: uppercase; transition: all 0.3s ease;
    }
    .just-link-btn:hover { background-color: #1a73e8; color: white !important; }
    .euro-value { color: #2e7d32; font-weight: 700; font-size: 1.05rem; }
    .weekly-value { color: #1a73e8; font-weight: 700; font-size: 1.05rem; }
    .pos-ret { color: #2e7d32; font-weight: 700; }
    .neg-ret { color: #d32f2f; font-weight: 700; }
    .small-metric-label { font-size: 0.9rem; color: #5f6368; font-weight: 500; }
    .small-metric-value { font-size: 1.25rem; font-weight: 800; color: #1a1c1e; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---
@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency: return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose') or t.info.get('currentPrice')
        return float(rate) if rate else 1.0
    except: return 1.0

def load_from_df(df):
    df = df.fillna(0)
    new_port = {}
    for _, row in df.iterrows():
        t = str(row['Ticker']).upper()
        new_port[t] = {
            'Nome': row.get('Nome', t), 
            'ISIN': str(row.get('ISIN', '')),
            'Politica': str(row.get('Politica', 'Acc')), 
            'TER': str(row.get('TER', '')),
            'Peso': float(row.get('Peso', 0)), 
            'Prezzo': float(row.get('Prezzo', 0)),
            'Valuta': str(row.get('Valuta', 'EUR')), 
            'Cambio': float(row.get('Cambio', 1.0)),
            'Investito_Reale': float(row.get('Investito_Reale', 0.0)),
            'Quote_Reali': float(row.get('Quote_Reali', 0.0))
        }
    st.session_state.portfolio = new_port
    if 'Total_Budget' in df.columns:
        st.session_state.total_budget = float(df['Total_Budget'].iloc[0])

def save_data_locally():
    if st.session_state.portfolio:
        df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
        df_save.to_csv(DB_FILE, index=False)
        return True
    return False

@st.cache_data(ttl=300)
def fetch_historical_data(tickers):
    if not tickers: return pd.DataFrame()
    data = yf.download(list(tickers), period="1y", progress=False)['Close']
    if len(tickers) == 1:
        data = data.to_frame()
        data.columns = list(tickers)
    return data.ffill().dropna()

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    if os.path.exists(DB_FILE):
        try: load_from_df(pd.read_csv(DB_FILE))
        except: pass

if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.title("📁 Gestione Portafoglio")

if st.sidebar.button("💾 SALVA PORTAFOGLIO", help="Salva permanentemente tutte le modifiche e gli acquisti nel file locale pac_data.csv"):
    if save_data_locally(): st.sidebar.success("Salvato correttamente!")

st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader("📥 Carica CSV", type="csv", help="Carica un file di portafoglio salvato in precedenza.")
if uploaded_file:
    load_from_df(pd.read_csv(uploaded_file))
    st.rerun()

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input(
    "Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget), step=50.0,
    help="Inserisci la cifra totale che intendi investire ogni mese. L'app la dividerà per te tra i vari ETF."
)

st.sidebar.markdown("<div class='search-container'>", unsafe_allow_html=True)
st.sidebar.subheader("🔍 Aggiungi ETF")
target_isin = st.sidebar.text_input("Inserisci ISIN", placeholder="es: IE00B4L5Y983", help="Inserisci il codice ISIN univoco dell'ETF che vuoi aggiungere.").strip().upper()
if st.sidebar.button("CERCA E AGGIUNGI", help="Recupera il nome e il prezzo in tempo reale da Yahoo Finance usando l'ISIN fornito."):
    if target_isin:
        try:
            with st.spinner("Analisi..."):
                y_obj = yf.Ticker(target_isin)
                info = y_obj.info
                st.session_state.portfolio[y_obj.ticker] = {
                    'Nome': info.get('longName', y_obj.ticker), 'ISIN': target_isin,
                    'Politica': 'Acc', 'TER': '0.20%', 'Peso': 0.0,
                    'Prezzo': float(info.get('currentPrice') or info.get('previousClose')),
                    'Valuta': info.get('currency', 'EUR'), 'Cambio': get_exchange_rate(info.get('currency', 'EUR')),
                    'Investito_Reale': 0.0, 'Quote_Reali': 0.0
                }
                st.rerun()
        except: st.sidebar.error("ISIN non trovato.")
st.sidebar.markdown("</div>", unsafe_allow_html=True)

# --- DASHBOARD PRINCIPALE ---
st.title("💰 Il mio Piano d'Accumulo")

if st.session_state.portfolio:
    cols = st.columns([2.5, 0.9, 0.8, 0.7, 1.0, 1.0, 0.8, 0.6])
    labels = ["Asset / JustETF", "Dati", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Quote S.", "Azione"]
    for col, lab in zip(cols, labels): col.write(f"**{lab}**")

    tot_w = 0
    total_invested_all = 0
    current_value_all = 0

    for ticker, asset in st.session_state.portfolio.items():
        if 'Investito_Reale' not in asset: asset['Investito_Reale'] = 0.0
        if 'Quote_Reali' not in asset: asset['Quote_Reali'] = 0.0

        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.5, 0.9, 0.8, 0.7, 1.0, 1.0, 0.8, 0.6])
        
        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        inv_m = (asset['Peso'] / 100) * st.session_state.total_budget
        inv_w = inv_m / 4.33
        val_attuale = asset['Quote_Reali'] * p_eur
        total_invested_all += asset['Investito_Reale']
        current_value_all += val_attuale

        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:40]}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='isin-display'>{asset['ISIN']}</div>", unsafe_allow_html=True)
            if asset['Investito_Reale'] > 0:
                diff = val_attuale - asset['Investito_Reale']
                st.markdown(f"<div class='real-status'>Reale: {val_attuale:,.2f}€ ({(diff):+,.2f}€)</div>", unsafe_allow_html=True)
            url_just = f"https://www.justetf.com/it/etf-profile.html?isin={asset['ISIN']}"
            st.markdown(f"<a href='{url_just}' target='_blank' class='just-link-btn'>JustETF</a>", unsafe_allow_html=True)

        with c2:
            asset['Politica'] = st.selectbox("T", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"p_{ticker}", label_visibility="collapsed", help="Seleziona se l'ETF accumula i dividendi (Acc) o li distribuisce (Dist).")
            asset['TER'] = st.text_input("T", asset['TER'], key=f"t_{ticker}", label_visibility="collapsed", help="Inserisci il TER (costo annuo) indicato sulla scheda tecnica.")

        c3.write(f"**{p_eur:.2f}**")
        w = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed", help="Quale percentuale del tuo budget mensile vuoi destinare a questo ETF?")
        asset['Peso'] = w
        tot_w += w
        
        c5.markdown(f"<span class='euro-value'>{inv_m:,.2f}</span>", unsafe_allow_html=True)
        c6.markdown(f"<span class='weekly-value'>{inv_w:,.2f}</span>", unsafe_allow_html=True)
        c7.write(f"{inv_w/p_eur if p_eur>0 else 0:.2f}")

        with c8:
            if st.button("➕", key=f"buy_{ticker}", help="Registra l'acquisto della tua quota settimanale. Aggiunge i soldi al capitale investito e calcola le quote ottenute al prezzo di oggi."):
                asset['Investito_Reale'] += inv_w
                asset['Quote_Reali'] += (inv_w / p_eur) if p_eur > 0 else 0
                st.toast(f"Acquisto registrato per {ticker}")
                st.rerun()
            if st.button("🗑️", key=f"d_{ticker}", help="Rimuovi definitivamente questo asset dal tuo piano."):
                del st.session_state.portfolio[ticker]; st.rerun()

    st.markdown("---")

    # --- REALE VS STORICA ---
    if total_invested_all > 0:
        st.subheader("🏦 Riepilogo Portafoglio Reale")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Capitale Versato", f"{total_invested_all:,.2f} €", help="Somma totale di tutti i tasti '+' premuti finora.")
        r2.metric("Valore Attuale", f"{current_value_all:,.2f} €", help="Valore delle tue quote accumulate calcolato ai prezzi di mercato attuali.")
        r3.metric("Profit & Loss", f"{(current_value_all - total_invested_all):+,.2f} €", f"{((current_value_all/total_invested_all)-1)*100:+.2f}%", help="Guadagno o perdita totale del tuo portafoglio reale.")
        if r4.button("🧹 Reset Dati Reali", help="ATTENZIONE: Azzera definitivamente tutto lo storico dei tuoi acquisti reali per ricominciare da zero."):
            for t in st.session_state.portfolio:
                st.session_state.portfolio[t]['Investito_Reale'] = 0.0
                st.session_state.portfolio[t]['Quote_Reali'] = 0.0
            st.rerun()

    # --- ANALISI STORICA ---
    st.subheader("📈 Analisi Storica Strategia (Ultimi 12 mesi)")
    active_tickers = [t for t in st.session_state.portfolio if st.session_state.portfolio[t]['Peso'] > 0]
    
    if active_tickers:
        try:
            data = fetch_historical_data(tuple(active_tickers))
            if not data.empty:
                tot_w_ins = sum(st.session_state.portfolio[t]['Peso'] for t in active_tickers)
                norm = (data / data.iloc[0]) * 100
                port_line = pd.Series(0.0, index=norm.index)
                for t in active_tickers:
                    port_line += norm[t] * (st.session_state.portfolio[t]['Peso'] / tot_w_ins)
                
                m1, m2, m3 = st.columns(3)
                with m1: st.markdown(f"<div class='small-metric-label'>Rendimento PAC (1A)</div><div class='small-metric-value'>{port_line.iloc[-1]-100:+.2f}%</div>", unsafe_allow_html=True)
                with m2: st.markdown(f"<div class='small-metric-label'>Rendimento PAC (6M)</div><div class='small-metric-value'>{((port_line.iloc[-1]/port_line.iloc[-len(port_line)//2])-1)*100:+.2f}%</div>", unsafe_allow_html=True)
                with m3:
                    perf_etf = ((data.iloc[-1]/data.iloc[0])-1)*100
                    bt = perf_etf.idxmax()
                    st.markdown(f"<div class='small-metric-label'>🏆 Miglior Asset (1A)</div><div style='color:#1a73e8; font-weight:800; font-size:1rem;'>{st.session_state.portfolio[bt]['Nome'][:30]}...</div><div class='pos-ret'>{perf_etf.max():+.2f}%</div>", unsafe_allow_html=True)

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=port_line.index, y
