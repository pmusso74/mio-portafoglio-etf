import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner Pro", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv"
UPDATE_INTERVAL = 600 

# --- CACHING ---
@st.cache_data(ttl=3600)
def get_historical_data(tickers):
    if not tickers: return None
    return yf.download(list(tickers), period="1y", progress=False)['Close']

@st.cache_data(ttl=86400)
def get_exchange_rate(from_currency):
    if from_currency == "EUR": return 1.0
    try:
        pair = f"{from_currency}EUR=X"
        rate = yf.Ticker(pair).fast_info.last_price
        return float(rate)
    except: return 1.0

# --- FUNZIONI PERSISTENZA (AUTOSAVE) ---
def save_data():
    if st.session_state.portfolio:
        df = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
        df.to_csv(DB_FILE, index=False)

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        if not df.empty:
            st.session_state.total_budget = float(df['Total_Budget'].iloc[0])
            for _, row in df.iterrows():
                ticker = row['Ticker']; data = row.to_dict()
                del data['Ticker']; del data['Total_Budget']
                st.session_state.portfolio[ticker] = data

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    load_data()
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0.0
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- CALLBACK PER AGGIORNAMENTO ISTANTANEO ---
def sync_weight(ticker):
    st.session_state.portfolio[ticker]['Peso'] = st.session_state[f"input_w_{ticker}"]
    save_data()

# --- FUNZIONI CORE ---
def detect_policy(inf, nome):
    y_val = inf.get('dividendYield') or inf.get('trailingAnnualDividendYield') or 0
    return "Dist" if y_val > 0 or "dist" in nome.lower() else "Acc"

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
                st.session_state.portfolio[ticker]['Politica'] = detect_policy(i, st.session_state.portfolio[ticker]['Nome'])
        except: continue
    st.session_state.last_update = time.time()
    save_data()

if (time.time() - st.session_state.last_update) > UPDATE_INTERVAL:
    update_all_prices()

# --- CSS ORIGINALE ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #eee; }
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 0.95rem; line-height: 1.1; }
    .ticker-label { color: #666; font-family: monospace; font-size: 0.8rem; }
    .tipo-tag { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; color: white; }
    .acc-tag { background-color: #1a73e8; }
    .dist-tag { background-color: #f29900; }
    .real-status { color: #2e7d32; font-size: 0.75rem; font-weight: 600; margin-top: 3px; }
    .just-link-btn { 
        display: inline-block; margin-top: 5px; padding: 2px 10px; 
        background-color: #ffffff; color: #1a73e8 !important; 
        text-decoration: none !important; border: 1px solid #1a73e8;
        border-radius: 4px; font-size: 0.65rem; font-weight: 700;
    }
    .budget-box { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #1a73e8; margin-bottom: 20px; }
    .weight-warning { color: #d32f2f; font-weight: bold; }
    .weight-ok { color: #2e7d32; font-weight: bold; }
    .rebalance-hint { font-size: 0.75rem; color: #1a73e8; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("📊 Configurazione")
old_budget = st.session_state.total_budget
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0)
if old_budget != st.session_state.total_budget: save_data()

with st.sidebar.expander("➕ Aggiungi ETF", expanded=False):
    new_t = st.text_input("Ticker Yahoo (es. SWDA.MI)").strip().upper()
    if st.button("Aggiungi Asset"):
        try:
            y = yf.Ticker(new_t); i = y.info; n = i.get('shortName', new_t)
            curr = i.get('currency', 'EUR')
            st.session_state.portfolio[new_t] = {
                'Nome': n, 'ISIN': i.get('underlyingSymbol') or (y.isin if hasattr(y, 'isin') else ""),
                'Politica': detect_policy(i, n), 'TER': '0.20%', 'Peso': 0.0,
                'Prezzo': i.get('currentPrice') or i.get('regularMarketPrice'),
                'Valuta': curr, 'Cambio': get_exchange_rate(curr),
                'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            save_data(); st.rerun()
        except: st.error("Non trovato")

st.sidebar.markdown("---")
if st.sidebar.button("🔄 AGGIORNA PREZZI", use_container_width=True):
    update_all_prices(); st.rerun()

if st.sidebar.button("🧹 RESET DATI REALI", use_container_width=True):
    for t in st.session_state.portfolio:
        st.session_state.portfolio[t]['Investito_Reale'] = 0.0
        st.session_state.portfolio[t]['Quote_Reali'] = 0.0
    save_data(); st.rerun()

# --- LOGICA SMART REBALANCING ---
total_val_portafoglio = sum(a['Quote_Reali'] * a['Prezzo'] * a['Cambio'] for a in st.session_state.portfolio.values())
target_val_finale = total_val_portafoglio + st.session_state.total_budget
allocazione_smart = {}
for t, a in st.session_state.portfolio.items():
    v_ideale = target_val_finale * (a['Peso'] / 100)
    v_attuale = a['Quote_Reali'] * a['Prezzo'] * a['Cambio']
    allocazione_smart[t] = max(0, v_ideale - v_attuale)
# Normalizzazione budget
somma_smart = sum(allocazione_smart.values())
if somma_smart > st.session_state.total_budget and somma_smart > 0:
    r = st.session_state.total_budget / somma_smart
    for t in allocazione_smart: allocazione_smart[t] *= r

# --- MAIN ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("Aggiungi un ETF dalla barra laterale per iniziare.")
else:
    somma_pesi = round(sum(a['Peso'] for a in st.session_state.portfolio.values()), 2)
    if somma_pesi != 100:
        st.markdown(f"⚠️ <span class='weight-warning'>Somma pesi: {somma_pesi}% (Deve essere 100%)</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"✅ <span class='weight-ok'>Somma pesi: {somma_pesi}%</span>", unsafe_allow_html=True)

    # Tabella Intestazione ORIGINALE
    h = st.columns([2.2, 0.6, 0.7, 0.7, 0.9, 0.9, 0.7, 1.2])
    for col, text in zip(h, ["Asset", "Tipo", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Drift", "Azioni"]): col.write(f"**{text}**")

    for ticker, asset in list(st.session_state.portfolio.items()):
        p_eur = asset['Prezzo'] * asset['Cambio']
        v_attuale = asset['Quote_Reali'] * p_eur
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.2, 0.6, 0.7, 0.7, 0.9, 0.9, 0.7, 1.2])
        
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:35]}</div><div class='ticker-label'>{ticker} ({asset['Valuta']})</div>", unsafe_allow_html=True)
            if v_attuale > 0: st.markdown(f"<div class='real-status'>Valore: {v_attuale:,.2f}€</div>", unsafe_allow_html=True)
            url = f"https://www.justetf.com/it/etf-profile.html?isin={asset.get('ISIN','')}"
            st.markdown(f"<a href='{url}' target='_blank' class='just-link-btn'>JustETF ↗</a>", unsafe_allow_html=True)

        with c2: st.markdown(f"<br><span class='tipo-tag {'acc-tag' if asset['Politica']=='Acc' else 'dist-tag'}'>{asset['Politica']}</span>", unsafe_allow_html=True)
        c3.write(f"<br>{p_eur:,.2f}", unsafe_allow_html=True)
        c4.number_input("%", 0, 100, int(asset['Peso']), key=f"input_w_{ticker}", on_change=sync_weight, args=(ticker,), label_visibility="collapsed")
        
        target_eur = (asset['Peso'] / 100) * st.session_state.total_budget
        c5.write(f"**{target_eur:,.2f}**")
        # Mostra suggerimento Smart Rebalancing sotto il target
        c5.markdown(f"<div class='rebalance-hint'>Smart: {allocazione_smart[ticker]:,.2f}</div>", unsafe_allow_html=True)
        c6.write(f"{target_eur / 4.33:,.2f}")
        
        with c7:
            if total_val_portafoglio > 0:
                drift = ((v_attuale / total_val_portafoglio) * 100) - asset['Peso']
                st.write(f"<br>{drift:+.1f}%", unsafe_allow_html=True)
            else: st.write("<br>-", unsafe_allow_html=True)

        with c8:
            st.write("") # Spazio
            act1, act2, act3 = st.columns(3)
            if act1.button("➕", key=f"add_{ticker}", help="Aggiungi quota Smart"):
                asset['Investito_Reale'] += allocazione_smart[ticker]
                asset['Quote_Reali'] += (allocazione_smart[ticker] / p_eur) if p_eur > 0 else 0
                save_data(); st.rerun()
            if act2.button("➖", key=f"sub_{ticker}"):
                asset['Investito_Reale'] = max(0, asset['Investito_Reale'] - target_eur)
                asset['Quote_Reali'] = max(0, asset['Quote_Reali'] - (target_eur / p_eur))
                save_data(); st.rerun()
            if act3.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; save_data(); st.rerun()

    # --- RIEPILOGO ---
    st.markdown("---")
    tot_investito_reale = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_investito_reale:,.2f} €")
    m2.metric("Valore Attuale", f"{total_val_portafoglio:,.2f} €")
    m3.metric("Profit/Loss", f"{total_val_portafoglio - tot_investito_reale:,.2f} €", f"{((total_val_portafoglio/tot_investito_reale)-1)*100 if tot_investito_reale>0 else 0:+.2f}%")

    st.markdown("---")
    c_info, c_pie = st.columns([1, 1.5])
    with c_info:
        st.subheader("🏦 Stato dell'Investimento")
        st.markdown("<div class='budget-box'>", unsafe_allow_html=True)
        st.write(f"**Budget Mensile PAC:** {st.session_state.total_budget:,.2f} €")
        rapporto = tot_investito_reale / st.session_state.total_budget if st.session_state.total_budget > 0 else 0
        st.write(f"**Copertura Piano:** {rapporto:.1f} mensilità.")
        st.progress(min(rapporto / 24, 1.0))
        st.markdown("</div>", unsafe_allow_html=True)
    with c_pie:
        if total_val_portafoglio > 0:
            df_pie = pd.DataFrame([{'Asset': a['Nome'], 'Valore': a['Quote_Reali'] * a['Prezzo'] * a['Cambio']} for a in st.session_state.portfolio.values() if a['Quote_Reali'] > 0])
            fig_p = px.pie(df_pie, values='Valore', names='Asset', hole=0.4, title="Distribuzione Reale (€)")
            fig_p.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_p, use_container_width=True)

    # --- PERFORMANCE STORICA ---
    st.markdown("---")
    st.subheader("📊 Performance Storica (1 Anno)")
    try:
        tks = tuple(st.session_state.portfolio.keys())
        data = get_historical_data(tks)
        if data is not None:
            norm = (data / data.iloc[0]) * 100
            returns_1y = ((data.iloc[-1] / data.iloc[0]) - 1) * 100
            pesi_list = [st.session_state.portfolio[t]['Peso'] for t in list(data.columns)]
            somma_p = sum(pesi_list) if sum(pesi_list) > 0 else 1
            pac_perf_1y = sum(returns_1y[t] * (st.session_state.portfolio[t]['Peso'] / somma_p) for t in data.columns)
            
            perf_c1, perf_c2, perf_c3 = st.columns(3)
            perf_c1.metric("Rendimento PAC (1 Anno)", f"{pac_perf_1y:+.2f}%")
            best_t = returns_1y.idxmax()
            perf_c3.metric("Miglior Asset", f"{best_t}", f"{returns_1y.max():+.2f}%")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=norm.index, y=(norm * pesi_list).sum(axis=1)/somma_p, name="⭐ IL TUO PAC", line=dict(color='red', width=4)))
            for t in data.columns:
                fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=t, line=dict(width=1.5), opacity=0.4))
            fig.update_layout(template="plotly_white", height=400, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)
    except: st.warning("Dati storici non disponibili al momento.")

st.sidebar.caption(f"Ultimo agg: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))}")
