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
    .stButton button { width: 100%; padding: 2px 5px; }
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

def update_all_prices():
    if not st.session_state.portfolio: return
    with st.spinner("Aggiornamento dati di borsa..."):
        for ticker in st.session_state.portfolio:
            try:
                y_obj = yf.Ticker(ticker)
                new_price = y_obj.info.get('currentPrice') or y_obj.info.get('regularMarketPrice') or y_obj.info.get('previousClose')
                if new_price: st.session_state.portfolio[ticker]['Prezzo'] = float(new_price)
                curr = st.session_state.portfolio[ticker]['Valuta']
                st.session_state.portfolio[ticker]['Cambio'] = get_exchange_rate(curr)
            except: continue
        st.toast("✅ Prezzi aggiornati!")

def load_from_df(df):
    df = df.fillna(0)
    new_port = {}
    for _, row in df.iterrows():
        t = str(row['Ticker']).upper()
        new_port[t] = {
            'Nome': row.get('Nome', t), 'ISIN': str(row.get('ISIN', '')),
            'Politica': str(row.get('Politica', 'Acc')), 'TER': str(row.get('TER', '')),
            'Peso': float(row.get('Peso', 0)), 'Prezzo': float(row.get('Prezzo', 0)),
            'Valuta': str(row.get('Valuta', 'EUR')), 'Cambio': float(row.get('Cambio', 1.0)),
            'Investito_Reale': float(row.get('Investito_Reale', 0.0)),
            'Quote_Reali': float(row.get('Quote_Reali', 0.0))
        }
    st.session_state.portfolio = new_port
    if 'Total_Budget' in df.columns: st.session_state.total_budget = float(df['Total_Budget'].iloc[0])

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
    if len(tickers) == 1: data = data.to_frame(); data.columns = list(tickers)
    return data.ffill().dropna()

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    if os.path.exists(DB_FILE):
        try: load_from_df(pd.read_csv(DB_FILE))
        except: pass
if 'total_budget' not in st.session_state: st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.title("📁 Gestione Portafoglio")
cs1, cs2 = st.sidebar.columns(2)
if cs1.button("💾 SALVA"):
    if save_data_locally(): st.sidebar.success("Salvato!")
if cs2.button("🔄 AGGIORNA"):
    update_all_prices()
    st.rerun()

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("📥 Carica CSV", type="csv")
if uploaded_file:
    load_from_df(pd.read_csv(uploaded_file))
    st.rerun()

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget), step=50.0)

st.sidebar.markdown("<div class='search-container'>", unsafe_allow_html=True)
st.sidebar.subheader("🔍 Aggiungi ETF")
target_isin = st.sidebar.text_input("Inserisci ISIN").strip().upper()
if st.sidebar.button("CERCA E AGGIUNGI"):
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

# --- MAIN ---
st.title("💰 Il mio Piano d'Accumulo")

if st.session_state.portfolio:
    cols = st.columns([2.5, 0.9, 0.8, 0.7, 1.0, 1.0, 0.8, 1.0])
    labels = ["Asset / JustETF", "Dati", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Quote S.", "Azioni"]
    for col, lab in zip(cols, labels): col.write(f"**{lab}**")

    tot_w, total_invested_all, current_value_all = 0, 0, 0
    all_tickers = list(st.session_state.portfolio.keys())

    for ticker, asset in st.session_state.portfolio.items():
        if 'Investito_Reale' not in asset: asset['Investito_Reale'] = 0.0
        if 'Quote_Reali' not in asset: asset['Quote_Reali'] = 0.0

        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.5, 0.9, 0.8, 0.7, 1.0, 1.0, 0.8, 1.0])
        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        inv_m = (asset['Peso'] / 100) * st.session_state.total_budget
        inv_w = inv_m / 4.33
        val_attuale = asset['Quote_Reali'] * p_eur
        total_invested_all += asset['Investito_Reale']
        current_value_all += val_attuale

        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:40]}</div><div class='isin-display'>{asset['ISIN']}</div>", unsafe_allow_html=True)
            if asset['Investito_Reale'] > 0:
                st.markdown(f"<div class='real-status'>Reale: {val_attuale:,.2f}€ ({(val_attuale-asset['Investito_Reale']):+,.2f}€)</div>", unsafe_allow_html=True)
            st.markdown(f"<a href='https://www.justetf.com/it/etf-profile.html?isin={asset['ISIN']}' target='_blank' class='just-link-btn'>JustETF</a>", unsafe_allow_html=True)

        with c2:
            asset['Politica'] = st.selectbox("T", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"p_{ticker}", label_visibility="collapsed")
            asset['TER'] = st.text_input("T", asset['TER'], key=f"t_{ticker}", label_visibility="collapsed")

        c3.write(f"**{p_eur:.2f}**")
        w = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        asset['Peso'] = w
        tot_w += w
        c5.markdown(f"<span class='euro-value'>{inv_m:,.2f}</span>", unsafe_allow_html=True)
        c6.markdown(f"<span class='weekly-value'>{inv_w:,.2f}</span>", unsafe_allow_html=True)
        c7.write(f"{inv_w/p_eur if p_eur>0 else 0:.2f}")

        with c8:
            act = st.columns(3)
            if act[0].button("➕", key=f"b_{ticker}"):
                asset['Investito_Reale'] += inv_w
                asset['Quote_Reali'] += (inv_w / p_eur) if p_eur > 0 else 0
                st.rerun()
            if act[1].button("➖", key=f"r_{ticker}"):
                if asset['Investito_Reale'] >= inv_w:
                    asset['Investito_Reale'] -= inv_w
                    asset['Quote_Reali'] = max(0.0, asset['Quote_Reali'] - (inv_w / p_eur)) if p_eur > 0 else 0
                    st.rerun()
            if act[2].button("🗑️", key=f"d_{ticker}"):
                del st.session_state.portfolio[ticker]; st.rerun()

    st.markdown("---")

    # --- PERFORMANCE REALE ---
    if total_invested_all > 0:
        st.subheader("🏦 Riepilogo Portafoglio Reale")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Capitale Versato", f"{total_invested_all:,.2f} €")
        r2.metric("Valore Attuale", f"{current_value_all:,.2f} €")
        r3.metric("Profit & Loss", f"{(current_value_all - total_invested_all):+,.2f} €", f"{((current_value_all/total_invested_all)-1)*100:+.2f}%")
        if r4.button("🧹 Reset Dati Reali"):
            for t in st.session_state.portfolio:
                st.session_state.portfolio[t]['Investito_Reale'], st.session_state.portfolio[t]['Quote_Reali'] = 0.0, 0.0
            st.rerun()

    # --- ANALISI STORICA ---
    st.subheader("📈 Analisi Storica Strategia")
    active_tickers = [t for t in all_tickers if st.session_state.portfolio[t]['Peso'] > 0]
    if active_tickers:
        try:
            data = fetch_historical_data(tuple(all_tickers))
            if not data.empty:
                tot_w_ins = sum(st.session_state.portfolio[t]['Peso'] for t in active_tickers)
                norm = (data / data.iloc[0]) * 100
                port_line = pd.Series(0.0, index=norm.index)
                for t in active_tickers:
                    port_line += norm[t] * (st.session_state.portfolio[t]['Peso'] / tot_w_ins)
                
                # Metriche
                m1, m2, m3 = st.columns(3)
                m1.markdown(f"<div class='small-metric-label'>Rendimento 1 Anno</div><div class='small-metric-value'>{port_line.iloc[-1]-100:+.2f}%</div>", unsafe_allow_html=True)
                m2.markdown(f"<div class='small-metric-label'>Rendimento 6 Mesi</div><div class='small-metric-value'>{((port_line.iloc[-1]/port_line.iloc[-len(port_line)//2])-1)*100:+.2f}%</div>", unsafe_allow_html=True)
                perf_ind = ((data[active_tickers].iloc[-1]/data[active_tickers].iloc[0])-1)*100
                bt = perf_ind.idxmax()
                m3.markdown(f"<div class='small-metric-label'>🏆 Migliore Asset</div><div style='color:#1a73e8; font-weight:800;'>{st.session_state.portfolio[bt]['Nome'][:35]}...</div><div class='pos-ret'>{perf_ind.max():+.2f}%</div>", unsafe_allow_html=True)

                # GRAFICO 1: STORICO CUMULATIVO
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=port_line.index, y=port_line, name="IL TUO PAC", line=dict(color='#FF3B30', width=5)))
                for t in active_tickers:
                    fig1.add_trace(go.Scatter(x=norm.index, y=norm[t], name=st.session_state.portfolio[t]['Nome'][:20], line=dict(width=2), opacity=0.7))
                fig1.update_layout(title="Andamento Cumulativo 1 Anno (Base 100)", template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.15))
                st.plotly_chart(fig1, use_container_width=True)

                # GRAFICO 2: VARIAZIONI GIORNALIERE (RICHIESTA UTENTE)
                st.subheader("📊 Volatilità Giornaliera (%)")
                daily_rets = data[active_tickers].pct_change() * 100
                pac_daily = (daily_rets * [st.session_state.portfolio[t]['Peso']/tot_w_ins for t in active_tickers]).sum(axis=1)
                
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=pac_daily.index, y=pac_daily, name="VARIAZIONE PAC", line=dict(color='#FF3B30', width=2), fill='tozeroy'))
                for t in active_tickers:
                    fig2.add_trace(go.Scatter(x=daily_rets.index, y=daily_rets[t], name=t, line=dict(width=1), opacity=0.4))
                fig2.update_layout(title="Performance Giornaliera (%)", template="plotly_white", hovermode="x unified", yaxis_title="% Cambio Giorno")
                st.plotly_chart(fig2, use_container_width=True)

                # Dettaglio Rendimenti
                for t in active_tickers:
                    r1a, r6m = ((data[t].iloc[-1]/data[t].iloc[0])-1)*100, ((data[t].iloc[-1]/data[t].iloc[-len(data)//2])-1)*100
                    ca, cb, cc, cd = st.columns([3, 1, 1, 2])
                    ca.write(f"**{st.session_state.portfolio[t]['Nome']}**")
                    cb.markdown(f"<span class='{'pos-ret' if r1a>=0 else 'neg-ret'}'>1A: {r1a:+.2f}%</span>", unsafe_allow_html=True)
                    cc.markdown(f"<span class='{'pos-ret' if r6m>=0 else 'neg-ret'}'>6M: {r6m:+.2f}%</span>", unsafe_allow_html=True)
                    cd.write(f"{data[t].iloc[0]:.2f}€ → {data[t].iloc[-1]:.2f}€")
        except: st.error("Errore dati Yahoo Finance.")
else:
    st.info("👈 Inserisci un ISIN per iniziare.")
