import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import urllib.parse
import re
import os
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF Portfolio & PAC Tracker", layout="wide", page_icon="📈")
DB_FILE = "pac_data_v2.csv"

# --- CSS ESTETICA ---
st.markdown("""
    <style>
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 1.1rem; }
    .isin-display { color: #d32f2f; font-weight: bold; font-family: monospace; font-size: 0.9rem; }
    .search-container { background-color: #f0f7ff; padding: 15px; border-radius: 10px; border: 1px solid #1a73e8; margin-bottom: 20px; }
    .euro-value { color: #2e7d32; font-weight: 700; }
    .weekly-value { color: #1a73e8; font-weight: 700; }
    .metric-box { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI SUPPORTO ---
@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency: return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose') or t.info.get('currentPrice')
        return float(rate) if rate else 1.0
    except: return 1.0

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE).fillna("")
        # Carica Piano
        plan_df = df[df['Tipo_Dato'] == 'Piano']
        for _, row in plan_df.iterrows():
            st.session_state.portfolio[row['Ticker']] = {
                'Nome': row['Nome'], 'ISIN': row['ISIN'], 'Politica': row['Politica'], 
                'TER': row['TER'], 'Peso': float(row['Peso']), 'Prezzo': float(row['Prezzo']),
                'Valuta': row['Valuta'], 'Cambio': float(row['Cambio'])
            }
        # Carica Acquisti
        buy_df = df[df['Tipo_Dato'] == 'Acquisto']
        st.session_state.history = buy_df.to_dict('records')
        
        if not plan_df.empty:
            st.session_state.total_budget = float(plan_df['Total_Budget'].iloc[0])

def save_data():
    data = []
    for k, v in st.session_state.portfolio.items():
        data.append({**{'Ticker': k, 'Tipo_Dato': 'Piano', 'Total_Budget': st.session_state.total_budget}, **v})
    for h in st.session_state.history:
        data.append({**h, 'Tipo_Dato': 'Acquisto'})
    pd.DataFrame(data).to_csv(DB_FILE, index=False)

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state: st.session_state.portfolio = {}
if 'history' not in st.session_state: st.session_state.history = []
if 'total_budget' not in st.session_state: 
    st.session_state.total_budget = 1000.0
    load_data()

# --- SIDEBAR ---
st.sidebar.title("📁 Gestione & Monitoraggio")
if st.sidebar.button("💾 SALVA TUTTO"):
    save_data()
    st.sidebar.success("Dati salvati!")

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget), step=50.0)
st.sidebar.info(f"Settimanale: {st.session_state.total_budget/4.33:,.2f} €")

# BOX AGGIUNTA ETF
st.sidebar.markdown("<div class='search-container'>", unsafe_allow_html=True)
st.sidebar.subheader("🔍 Aggiungi ETF al Piano")
target_isin = st.sidebar.text_input("Inserisci ISIN").strip().upper()
if st.sidebar.button("Aggiungi"):
    try:
        y_obj = yf.Ticker(target_isin)
        info = y_obj.info
        st.session_state.portfolio[y_obj.ticker] = {
            'Nome': info.get('longName', y_obj.ticker), 'ISIN': target_isin,
            'Politica': 'Acc', 'TER': '0.20%', 'Peso': 0.0,
            'Prezzo': float(info.get('currentPrice') or info.get('previousClose')),
            'Valuta': info.get('currency', 'EUR'), 'Cambio': get_exchange_rate(info.get('currency', 'EUR'))
        }
        st.rerun()
    except: st.sidebar.error("ISIN non trovato.")
st.sidebar.markdown("</div>", unsafe_allow_html=True)

# --- TABS PRINCIPALI ---
tab_plan, tab_monitor = st.tabs(["📝 PIANIFICAZIONE PAC", "📈 MONITORAGGIO REALE"])

# --- TAB 1: PIANIFICAZIONE ---
with tab_plan:
    if st.session_state.portfolio:
        cols = st.columns([3, 1, 1, 1, 1, 1, 0.5])
        for col, lab in zip(cols, ["Asset", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Quote Sett.", ""]): col.write(f"**{lab}**")

        tot_w = 0
        for ticker, asset in st.session_state.portfolio.items():
            p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
            c1, c2, c3, c4, c5, c6, c7 = st.columns([3, 1, 1, 1, 1, 1, 0.5])
            with c1:
                st.markdown(f"<div class='etf-name'>{asset['Nome'][:40]}</div><div class='isin-display'>{asset['ISIN']}</div>", unsafe_allow_html=True)
            c2.write(f"{p_eur:.2f}")
            w = c3.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['Peso'] = w
            tot_w += w
            inv_m = (w/100) * st.session_state.total_budget
            inv_w = inv_m / 4.33
            c4.write(f"{inv_m:,.2f}")
            c5.write(f"{inv_w:,.2f}")
            c6.write(f"**{inv_w/p_eur if p_eur>0 else 0:.2f}**")
            if c7.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; st.rerun()
    else:
        st.info("Aggiungi un ETF dalla sidebar per iniziare.")

# --- TAB 2: MONITORAGGIO REALE ---
with tab_monitor:
    st.subheader("🛒 Registra Acquisto Settimanale")
    with st.expander("Clicca qui per aggiungere un acquisto fatto"):
        e1, e2, e3 = st.columns(3)
        etf_to_buy = e1.selectbox("Quale ETF hai comprato?", list(st.session_state.portfolio.keys()))
        amount_paid = e2.number_input("Quanto hai investito (€)?", min_value=0.0, value=st.session_state.total_budget/4.33/len(st.session_state.portfolio) if st.session_state.portfolio else 0.0)
        date_buy = e3.date_input("Data acquisto", datetime.now())
        
        if st.button("Registra Acquisto"):
            price_now = st.session_state.portfolio[etf_to_buy]['Prezzo'] * st.session_state.portfolio[etf_to_buy]['Cambio']
            shares_bought = amount_paid / price_now
            st.session_state.history.append({
                'Data': date_buy.strftime("%Y-%m-%d"), 'Ticker': etf_to_buy,
                'Investito': amount_paid, 'Quote': shares_bought, 'Prezzo_Acquisto': price_now
            })
            st.success("Acquisto registrato!")
            st.rerun()

    if st.session_state.history:
        # Calcolo statistiche portafoglio
        df_h = pd.DataFrame(st.session_state.history)
        summary = df_h.groupby('Ticker').agg({'Investito': 'sum', 'Quote': 'sum'}).reset_index()
        
        total_invested = summary['Investito'].sum()
        current_total_value = 0
        
        st.markdown("### 📊 Stato del Portafoglio Reale")
        m_cols = st.columns(4)
        
        rows_data = []
        for _, row in summary.iterrows():
            t = row['Ticker']
            price_live = st.session_state.portfolio[t]['Prezzo'] * st.session_state.portfolio[t]['Cambio']
            val_attuale = row['Quote'] * price_live
            current_total_value += val_attuale
            guadagno = val_attuale - row['Investito']
            perc = (guadagno / row['Investito']) * 100
            rows_data.append({
                'Asset': st.session_state.portfolio[t]['Nome'],
                'Investito': row['Investito'],
                'Valore Attuale': val_attuale,
                'Guadagno €': guadagno,
                'Guadagno %': perc
            })

        m_cols[0].metric("Totale Investito", f"{total_invested:,.2f} €")
        m_cols[1].metric("Valore Attuale", f"{current_total_value:,.2f} €", f"{(current_total_value-total_invested):+,.2f} €")
        m_cols[2].metric("Performance Totale", f"{((current_total_value/total_invested)-1)*100 if total_invested>0 else 0:+.2f} %")
        m_cols[3].metric("Numero Acquisti", len(st.session_state.history))

        st.table(pd.DataFrame(rows_data).style.format({'Investito': '{:.2f} €', 'Valore Attuale': '{:.2f} €', 'Guadagno €': '{:+.2f} €', 'Guadagno %': '{:+.2f} %'}))
        
        # Grafico Crescita
        df_h['Data'] = pd.to_datetime(df_h['Data'])
        df_h = df_h.sort_values('Data')
        df_h['Cumulativo'] = df_h['Investito'].cumsum()
        fig_growth = px.area(df_h, x='Data', y='Cumulativo', title="Crescita Capitale Versato nel Tempo", labels={'Cumulativo': 'Euro Versati'})
        st.plotly_chart(fig_growth, use_container_width=True)
        
        if st.button("🗑️ Cancella Cronologia"):
            st.session_state.history = []
            st.rerun()
    else:
        st.info("Non hai ancora registrato acquisti. Usa il modulo sopra quando compri le tue quote settimanali.")
