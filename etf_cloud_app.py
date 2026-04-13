import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner Pro v2", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv"
UPDATE_INTERVAL = 600 

# --- FUNZIONI DI COSTRUTTORE E SALVATAGGIO ---
def save_data():
    if st.session_state.portfolio:
        df = pd.DataFrame([
            {'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} 
            for k, v in st.session_state.portfolio.items()
        ])
        df.to_csv(DB_FILE, index=False)

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        if not df.empty:
            st.session_state.total_budget = float(df['Total_Budget'].iloc[0])
            for _, row in df.iterrows():
                ticker = row['Ticker']
                data = row.to_dict()
                del data['Ticker']
                del data['Total_Budget']
                st.session_state.portfolio[ticker] = data

# --- CACHING PER PERFORMANCE ---
@st.cache_data(ttl=3600)
def get_historical_data(tickers):
    if not tickers: return None
    data = yf.download(tickers, period="1y", progress=False)['Close']
    return data

@st.cache_data(ttl=86400)
def get_exchange_rate(from_currency):
    if from_currency == "EUR": return 1.0
    try:
        pair = f"{from_currency}EUR=X"
        rate = yf.Ticker(pair).info.get('regularMarketPrice') or yf.Ticker(pair).fast_info.last_price
        return float(rate)
    except:
        return 1.0

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    load_data()
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0.0
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- CALLBACKS ---
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
            currency = i.get('currency', 'EUR')
            if p:
                st.session_state.portfolio[ticker]['Prezzo'] = float(p)
                st.session_state.portfolio[ticker]['Valuta'] = currency
                st.session_state.portfolio[ticker]['Cambio'] = get_exchange_rate(currency)
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
    .rebalance-hint { color: #1a73e8; font-weight: bold; font-size: 0.85rem; background: #e8f0fe; padding: 2px 5px; border-radius: 4px; }
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

if st.sidebar.button("🔄 FORZA AGGIORNAMENTO", use_container_width=True):
    update_all_prices(); st.rerun()

if st.sidebar.button("🧹 RESET DATI", use_container_width=True):
    st.session_state.portfolio = {}; save_data(); st.rerun()

# --- LOGICA SMART REBALANCING ---
# Calcola come allocare il budget mensile per minimizzare il drift
total_val_attuale = sum(a['Quote_Reali'] * a['Prezzo'] * a['Cambio'] for a in st.session_state.portfolio.values())
target_val_finale = total_val_attuale + st.session_state.total_budget

allocazione_smart = {}
if total_val_attuale >= 0:
    for t, a in st.session_state.portfolio.items():
        valore_target_ideale = target_val_finale * (a['Peso'] / 100)
        valore_attuale_eur = a['Quote_Reali'] * a['Prezzo'] * a['Cambio']
        differenza = valore_target_ideale - valore_attuale_eur
        allocazione_smart[t] = max(0, differenza) # Non suggeriamo di vendere in un PAC

    # Normalizzazione se la somma dei suggerimenti supera il budget (capita se il drift è alto)
    somma_suggerimenti = sum(allocazione_smart.values())
    if somma_suggerimenti > 0:
        ratio = st.session_state.total_budget / somma_suggerimenti
        for t in allocazione_smart: allocazione_smart[t] *= min(1.0, ratio)

# --- MAIN ---
st.title("💰 ETF PAC Planner Pro v2")

if not st.session_state.portfolio:
    st.info("Aggiungi un ETF dalla barra laterale per iniziare.")
else:
    somma_pesi = sum(a['Peso'] for a in st.session_state.portfolio.values())
    st.warning(f"Somma pesi: {somma_pesi}%") if somma_pesi != 100 else st.success(f"Somma pesi: 100%")

    # Tabella Intestazione
    cols = st.columns([2, 0.5, 0.7, 0.7, 1, 1, 1])
    headers = ["Asset", "Tipo", "Prezzo", "Peso %", "Smart Buy €", "Drift", "Azioni"]
    for col, text in zip(cols, headers): col.write(f"**{text}**")

    for ticker, asset in list(st.session_state.portfolio.items()):
        p_eur = asset['Prezzo'] * asset['Cambio']
        v_attuale_eur = asset['Quote_Reali'] * p_eur
        
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 0.5, 0.7, 0.7, 1, 1, 1])
        
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:30]}</div><div class='ticker-label'>{ticker} ({asset['Valuta']})</div>", unsafe_allow_html=True)
            isin = asset.get('ISIN', '')
            url = f"https://www.justetf.com/it/etf-profile.html?isin={isin}" if len(str(isin)) > 5 else "#"
            st.markdown(f"<a href='{url}' target='_blank' style='font-size:0.7rem;'>JustETF ↗</a>", unsafe_allow_html=True)

        c2.markdown(f"<span class='tipo-tag {'acc-tag' if asset['Politica']=='Acc' else 'dist-tag'}'>{asset['Politica']}</span>", unsafe_allow_html=True)
        c3.write(f"{p_eur:,.2f}€")
        
        c4.number_input("%", 0, 100, int(asset['Peso']), key=f"input_w_{ticker}", on_change=sync_weight, args=(ticker,), label_visibility="collapsed")
        
        # Smart Buy (Allocazione suggerita)
        suggerito = allocazione_smart.get(ticker, 0)
        c5.markdown(f"<div class='rebalance-hint'>+{suggerito:,.2f} €</div>", unsafe_allow_html=True)
        
        with c6:
            if total_val_attuale > 0:
                drift = ((v_attuale_eur / total_val_attuale) * 100) - asset['Peso']
                st.write(f"{drift:+.1f}%")
            else: st.write("-")

        with c7:
            act1, act2, act3 = st.columns(3)
            if act1.button("➕", key=f"add_{ticker}", help="Registra acquisto smart suggerito"):
                asset['Investito_Reale'] += suggerito
                asset['Quote_Reali'] += (suggerito / p_eur) if p_eur > 0 else 0
                save_data(); st.rerun()
            if act2.button("➖", key=f"sub_{ticker}"):
                asset['Investito_Reale'] = max(0, asset['Investito_Reale'] - suggerito)
                asset['Quote_Reali'] = max(0, asset['Quote_Reali'] - (suggerito / p_eur))
                save_data(); st.rerun()
            if act3.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; save_data(); st.rerun()

    # --- RIEPILOGO METRICHE ---
    st.markdown("---")
    tot_investito = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_investito:,.2f} €")
    m2.metric("Valore Attuale", f"{total_val_attuale:,.2f} €")
    pnl = total_val_attuale - tot_investito
    pnl_perc = (pnl / tot_investito * 100) if tot_investito > 0 else 0
    m3.metric("Profit/Loss", f"{pnl:,.2f} €", f"{pnl_perc:+.2f}%")

    # --- PERFORMANCE STORICA CON CACHING ---
    st.subheader("📈 Performance Storica (1 Anno)")
    try:
        tks = list(st.session_state.portfolio.keys())
        hist_data = get_historical_data(tuple(tks)) # tuple per caching
        
        if hist_data is not None:
            # Calcolo cambi per i dati storici (semplificato all'ultimo cambio disponibile)
            # Per precisione millimetrica servirebbero i cambi storici, ma appesantirebbe troppo.
            norm = (hist_data / hist_data.iloc[0]) * 100
            
            fig = go.Figure()
            pesi = [st.session_state.portfolio[t]['Peso'] for t in tks]
            somma_p = sum(pesi) if sum(pesi) > 0 else 1
            
            # Linea Portafoglio
            portfolio_indexed = (norm * pesi).sum(axis=1) / somma_p
            fig.add_trace(go.Scatter(x=norm.index, y=portfolio_indexed, name="IL TUO PAC", line=dict(color='#1a73e8', width=4)))
            
            for t in tks:
                fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=f"{t}", line=dict(width=1), opacity=0.4))
            
            fig.update_layout(template="plotly_white", height=450, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info("Caricamento dati storici...")

st.sidebar.caption(f"Ultimo agg: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))}")
