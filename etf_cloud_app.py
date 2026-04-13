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

# --- FUNZIONI PERSISTENZA (AUTOSAVE) ---
def save_data():
    if st.session_state.portfolio:
        df = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
        df.to_csv(DB_FILE, index=False)

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                st.session_state.total_budget = float(df['Total_Budget'].iloc[0])
                for _, row in df.iterrows():
                    ticker = row['Ticker']; data = row.to_dict()
                    del data['Ticker']; del data['Total_Budget']
                    st.session_state.portfolio[ticker] = data
        except: pass

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    load_data()
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0.0
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

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
    .just-link-btn { 
        display: inline-block; margin-top: 5px; padding: 2px 10px; 
        background-color: #ffffff; color: #1a73e8 !important; 
        text-decoration: none !important; border: 1px solid #1a73e8;
        border-radius: 4px; font-size: 0.65rem; font-weight: 700;
    }
    .budget-box { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #1a73e8; margin-bottom: 20px; }
    .smart-hint { font-size: 0.72rem; color: #1a73e8; font-weight: 600; margin-top: 2px; }
    .weight-warning { color: #d32f2f; font-weight: bold; }
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

if st.sidebar.button("🔄 AGGIORNA PREZZI", use_container_width=True):
    update_all_prices(); st.rerun()

if st.sidebar.button("🧹 RESET DATI REALI", use_container_width=True):
    for t in st.session_state.portfolio:
        st.session_state.portfolio[t]['Investito_Reale'] = 0.0
        st.session_state.portfolio[t]['Quote_Reali'] = 0.0
    save_data(); st.rerun()

# --- LOGICA SMART REBALANCING (SOLO SUGGERIMENTO) ---
total_val_portafoglio = sum(a['Quote_Reali'] * a['Prezzo'] * a['Cambio'] for a in st.session_state.portfolio.values())
target_val_finale = total_val_portafoglio + st.session_state.total_budget
allocazione_smart = {}
for t, a in st.session_state.portfolio.items():
    v_ideale = target_val_finale * (a['Peso'] / 100)
    v_attuale = a['Quote_Reali'] * a['Prezzo'] * a['Cambio']
    allocazione_smart[t] = max(0, v_ideale - v_attuale)
# Normalizzazione budget smart
somma_smart = sum(allocazione_smart.values())
if somma_smart > 0:
    r = st.session_state.total_budget / somma_smart
    for t in allocazione_smart: allocazione_smart[t] *= min(1.0, r)

# --- MAIN ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("Aggiungi un ETF dalla barra laterale per iniziare.")
else:
    somma_pesi = round(sum(a['Peso'] for a in st.session_state.portfolio.values()), 2)
    if somma_pesi != 100:
        st.markdown(f"⚠️ <span class='weight-warning'>Somma pesi: {somma_pesi}% (Deve essere 100%)</span>", unsafe_allow_html=True)

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
        
        # Target Fisso Mensile e Settimanale
        target_mensile = (asset['Peso'] / 100) * st.session_state.total_budget
        target_settim = target_mensile / 4.33
        
        with c5:
            st.write(f"**{target_mensile:,.2f}**")
            st.markdown(f"<div class='smart-hint'>Smart: {allocazione_smart[ticker]:,.2f}</div>", unsafe_allow_html=True)
        
        c6.write(f"{target_settim:,.2f}")
        
        with c7:
            if total_val_portafoglio > 0:
                drift = ((v_attuale / total_val_portafoglio) * 100) - asset['Peso']
                st.write(f"<br>{drift:+.1f}%", unsafe_allow_html=True)
            else: st.write("<br>-", unsafe_allow_html=True)

        with c8:
            st.write("") 
            act1, act2, act3 = st.columns(3)
            # Il tasto + ora aggiunge la quota SETTIMANALE fissa
            if act1.button("➕", key=f"add_{ticker}", help=f"Aggiungi quota settimanale fissa ({target_settim:.2f}€)"):
                asset['Investito_Reale'] += target_settim
                asset['Quote_Reali'] += (target_settim / p_eur) if p_eur > 0 else 0
                save_data(); st.rerun()
            if act2.button("➖", key=f"sub_{ticker}"):
                asset['Investito_Reale'] = max(0, asset['Investito_Reale'] - target_settim)
                asset['Quote_Reali'] = max(0, asset['Quote_Reali'] - (target_settim / p_eur))
                save_data(); st.rerun()
            if act3.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; save_data(); st.rerun()

    # --- RIEPILOGO ---
    st.markdown("---")
    tot_investito_reale = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_investito_reale:,.2f} €")
    m2.metric("Valore Attuale", f"{total_val_portafoglio:,.2f} €")
    pnl = total_val_portafoglio - tot_investito_reale
    pnl_p = (pnl / tot_investito_reale * 100) if tot_investito_reale > 0 else 0
    m3.metric("Profit/Loss", f"{pnl:,.2f} €", f"{pnl_p:+.2f}%")

    st.markdown("---")
    c_info, c_pie = st.columns([1, 1.5])
    with c_info:
        st.subheader("🏦 Stato del Piano")
        st.markdown("<div class='budget-box'>", unsafe_allow_html=True)
        st.write(f"**Budget Mensile:** {st.session_state.total_budget:,.2f} €")
        st.write(f"**Investimento Settimanale:** {st.session_state.total_budget/4.33:,.2f} €")
        rapporto = tot_investito_reale / st.session_state.total_budget if st.session_state.total_budget > 0 else 0
        st.write(f"**Copertura:** {rapporto:.1f} mensilità versate.")
        st.progress(min(rapporto / 24, 1.0))
        st.markdown("</div>", unsafe_allow_html=True)
    with c_pie:
        if total_val_portafoglio > 0:
            df_pie = pd.DataFrame([{'Asset': a['Nome'], 'Valore': a['Quote_Reali'] * a['Prezzo'] * a['Cambio']} for a in st.session_state.portfolio.values() if a['Quote_Reali'] > 0])
            fig_p = px.pie(df_pie, values='Valore', names='Asset', hole=0.4, title="Distribuzione Reale")
            fig_p.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_p, use_container_width=True)

    # --- PERFORMANCE ---
    try:
        tks = tuple(st.session_state.portfolio.keys())
        data = get_historical_data(tks)
        if data is not None:
            st.markdown("---")
            st.subheader("📊 Performance Storica (1 Anno)")
            norm = (data / data.iloc[0]) * 100
            pesi_list = [st.session_state.portfolio[t]['Peso'] for t in list(data.columns)]
            somma_p = sum(pesi_list) if sum(pesi_list) > 0 else 1
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=norm.index, y=(norm * pesi_list).sum(axis=1)/somma_p, name="⭐ IL TUO PAC (Target)", line=dict(color='red', width=3)))
            for t in data.columns:
                fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=t, line=dict(width=1), opacity=0.4))
            fig.update_layout(template="plotly_white", height=400, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)
    except: pass

st.sidebar.caption(f"Ultimo agg: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))}")
