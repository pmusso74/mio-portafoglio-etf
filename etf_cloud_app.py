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

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- FUNZIONI DI CALLBACK (Per aggiornamento istantaneo) ---
def update_weight_in_state(ticker):
    # Questa funzione viene chiamata nel momento esatto in cui premi Enter sul peso
    st.session_state.portfolio[ticker]['Peso'] = st.session_state[f"w_input_{ticker}"]

def handle_purchase(ticker, amount, price, mode="add"):
    # Gestisce l'aggiunta o lo storno delle quote
    if price > 0:
        if mode == "add":
            st.session_state.portfolio[ticker]['Investito_Reale'] += amount
            st.session_state.portfolio[ticker]['Quote_Reali'] += (amount / price)
            st.toast(f"✅ Registrato acquisto per {ticker}")
        else:
            if st.session_state.portfolio[ticker]['Investito_Reale'] >= amount:
                st.session_state.portfolio[ticker]['Investito_Reale'] -= amount
                st.session_state.portfolio[ticker]['Quote_Reali'] = max(0.0, st.session_state.portfolio[ticker]['Quote_Reali'] - (amount / price))
                st.toast(f"➖ Stornato acquisto per {ticker}")

# --- CSS: FONT METRICHE E ESTETICA ---
st.markdown("""
    <style>
    [data-testid="stMetricLabel"] { font-size: 1.1rem !important; font-weight: 600 !important; }
    [data-testid="stMetricValue"] { font-size: 2.0rem !important; font-weight: 800 !important; color: #1a73e8 !important; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 1.0rem; line-height: 1.1; }
    .ticker-label { color: #d32f2f; font-family: monospace; font-size: 0.8rem; font-weight: bold; }
    .tipo-tag { padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white; }
    .acc-tag { background-color: #1a73e8; } .dist-tag { background-color: #f29900; }
    .real-status { color: #2e7d32; font-size: 0.85rem; font-weight: 700; background: #e8f5e9; padding: 2px 6px; border-radius: 4px; margin-top: 5px; display: inline-block; }
    .just-link-btn { display: inline-block; margin-top: 8px; padding: 4px 12px; background-color: #ffffff; color: #1a73e8 !important; text-decoration: none !important; border: 1px solid #1a73e8; border-radius: 20px; font-size: 0.7rem; font-weight: 700; }
    .budget-box { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #1a73e8; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("📁 Gestione Portafoglio")

uploaded_file = st.sidebar.file_uploader("📥 Carica Backup CSV", type="csv")
if uploaded_file:
    df_up = pd.read_csv(uploaded_file)
    for _, r in df_up.iterrows():
        st.session_state.portfolio[str(r['Ticker']).upper()] = {
            'Nome': r['Nome'], 'ISIN': r.get('ISIN', ''), 'Politica': r.get('Politica', 'Acc'),
            'Peso': float(r['Peso']), 'Prezzo': float(r['Prezzo']),
            'Investito_Reale': float(r['Investito_Reale']), 'Quote_Reali': float(r['Quote_Reali'])
        }
    st.session_state.total_budget = float(df_up['Total_Budget'].iloc[0])

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0)

col_s1, col_s2 = st.sidebar.columns(2)
if col_s1.button("💾 SALVA", use_container_width=True):
    df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
    df_save.to_csv(DB_FILE, index=False)
    st.sidebar.success("Salvato!")

if col_s2.button("🔄 AGGIORNA", use_container_width=True):
    for t in st.session_state.portfolio:
        try:
            y = yf.Ticker(t); p = y.info.get('currentPrice') or y.info.get('regularMarketPrice')
            if p: st.session_state.portfolio[t]['Prezzo'] = float(p)
        except: continue
    st.rerun()

if st.sidebar.button("🧹 RESET DATI REALI", use_container_width=True):
    for t in st.session_state.portfolio:
        st.session_state.portfolio[t]['Investito_Reale'] = 0.0
        st.session_state.portfolio[t]['Quote_Reali'] = 0.0
    st.rerun()

with st.sidebar.expander("➕ Aggiungi ETF"):
    nt = st.text_input("Ticker Yahoo").strip().upper()
    if st.button("Aggiungi"):
        try:
            y = yf.Ticker(nt); i = y.info
            st.session_state.portfolio[nt] = {
                'Nome': i.get('shortName', nt), 'ISIN': i.get('underlyingSymbol') or (y.isin if hasattr(y, 'isin') else ""),
                'Politica': 'Acc', 'Peso': 0.0, 'Prezzo': float(i.get('currentPrice') or i.get('regularMarketPrice')),
                'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            st.rerun()
        except: st.sidebar.error("Errore ticker")

# --- MAIN ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("👋 Inizia aggiungendo un ETF o caricando un file CSV.")
else:
    # 1. Calcolo Somma Pesi
    somma_pesi = sum(a['Peso'] for a in st.session_state.portfolio.values())
    if somma_pesi != 100:
        st.error(f"⚠️ Somma pesi: {somma_pesi:.1f}% (Deve essere 100%)")
    else:
        st.success(f"✅ Pesi configurati al 100%")

    # 2. Tabella
    h = st.columns([2.5, 0.6, 0.7, 0.7, 0.9, 0.9, 0.7, 1.2])
    for col, text in zip(h, ["Asset / Link", "Tipo", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Drift", "Azioni"]): col.write(f"**{text}**")

    tot_valore_reale = sum(v['Quote_Reali'] * v['Prezzo'] for v in st.session_state.portfolio.values())

    for ticker, asset in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.5, 0.6, 0.7, 0.7, 0.9, 0.9, 0.7, 1.2])
        
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:35]}</div><div class='ticker-label'>{ticker}</div>", unsafe_allow_html=True)
            v_reale = asset['Quote_Reali'] * asset['Prezzo']
            if asset['Quote_Reali'] > 0: st.markdown(f"<div class='real-status'>Posseduto: {v_reale:,.2f}€</div>", unsafe_allow_html=True)
            isin = asset.get('ISIN'); url = f"https://www.justetf.com/it/etf-profile.html?isin={isin}" if isin and len(str(isin))>5 else f"https://www.justetf.com/it/find-etf.html?query={ticker.split('.')[0]}"
            st.markdown(f"<a href='{url}' target='_blank' class='just-link-btn'>JustETF ↗</a>", unsafe_allow_html=True)

        with c2: st.markdown(f"<span class='tipo-tag {'acc-tag' if asset['Politica']=='Acc' else 'dist-tag'}'>{asset['Politica']}</span>", unsafe_allow_html=True)
        c3.write(f"{asset['Prezzo']:,.2f}")
        
        # PESO % CON CALLBACK (Aggiornamento istantaneo)
        c4.number_input("%", 0.0, 100.0, float(asset['Peso']), key=f"w_input_{ticker}", on_change=update_weight_in_state, args=(ticker,), label_visibility="collapsed")
        
        inv_m = (asset['Peso'] / 100) * st.session_state.total_budget
        inv_w = inv_m / 4.33
        c5.write(f"**{inv_m:,.2f}**")
        c6.write(f"{inv_w:,.2f}")
        
        with c7:
            if tot_valore_reale > 0:
                drift = ((v_reale / tot_valore_reale) * 100) - asset['Peso']
                st.write(f"{drift:+.1f}%")
            else: st.write("-")

        with c8:
            act1, act2, act3 = st.columns(3)
            # Pulsanti con gestione diretta dello stato
            if act1.button("➕", key=f"add_{ticker}", help="Registra acquisto mensile"):
                handle_purchase(ticker, inv_m, asset['Prezzo'], "add")
                st.rerun()
            if act2.button("➖", key=f"sub_{ticker}", help="Storna acquisto mensile"):
                handle_purchase(ticker, inv_m, asset['Prezzo'], "sub")
                st.rerun()
            if act3.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; st.rerun()

    # --- RIEPILOGO ---
    st.markdown("---")
    tot_investito = sum(v['Investito_Reale'] for v in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_investito:,.2f} €")
    m2.metric("Valore Attuale", f"{tot_valore_reale:,.2f} €")
    m3.metric("Profit/Loss", f"{tot_valore_reale - tot_investito:,.2f} €", f"{((tot_valore_reale/tot_investito)-1)*100 if tot_investito>0 else 0:+.2f}%")

    st.markdown("---")
    c_info, c_pie = st.columns([1, 1.5])
    with c_info:
        st.subheader("🏦 Riepilogo Piano")
        st.markdown("<div class='budget-box'>", unsafe_allow_html=True)
        st.write(f"**Budget Mensile:** {st.session_state.total_budget:,.2f} €")
        mens = tot_investito / st.session_state.total_budget if st.session_state.total_budget > 0 else 0
        st.write(f"**Mesi accumulati:** {mens:.1f}")
        st.progress(min(mens / 24, 1.0))
        st.markdown("</div>", unsafe_allow_html=True)
    with c_pie:
        pie_df = pd.DataFrame([{'Asset': v['Nome'], 'Valore': v['Quote_Reali'] * v['Prezzo']} for v in st.session_state.portfolio.values() if v['Quote_Reali'] > 0])
        if not pie_df.empty:
            st.plotly_chart(px.pie(pie_df, values='Valore', names='Asset', hole=0.4, title="Distribuzione Reale (€)"), use_container_width=True)

    # --- PERFORMANCE STORICA ---
    active_tks = [t for t in st.session_state.portfolio.keys() if st.session_state.portfolio[t]['Peso'] > 0]
    if active_tks:
        st.markdown("---")
        try:
            data = yf.download(active_tks, period="1y", progress=False)['Close']
            if len(active_tks) == 1: data = data.to_frame(); data.columns = active_tks
            norm = (data.ffill() / data.ffill().iloc[0]) * 100
            pesi = [st.session_state.portfolio[t]['Peso'] for t in active_tks]
            
            perf1, perf2, perf3 = st.columns(3)
            ret1y = ((data.iloc[-1]/data.iloc[0])-1)*100
            ret6m = ((data.iloc[-1]/data.iloc[len(data)//2])-1)*100
            perf1.metric("Rendimento PAC (1A)", f"{sum(ret1y[t]*(st.session_state.portfolio[t]['Peso']/sum(pesi)) for t in active_tks):+.2f}%")
            perf2.metric("Rendimento PAC (6M)", f"{sum(ret6m[t]*(st.session_state.portfolio[t]['Peso']/sum(pesi)) for t in active_tks):+.2f}%")
            best_t = ret1y.idxmax()
            perf3.metric("Top Asset (1A)", f"{st.session_state.portfolio[best_t]['Nome'][:15]}", f"{ret1y.max():+.2f}%")

            st.subheader("📈 Performance Storica (1 Anno)")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=norm.index, y=(norm * pesi).sum(axis=1)/sum(pesi), name="⭐ IL TUO PAC", line=dict(color='red', width=4), zorder=10))
            for t in active_tks: fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=st.session_state.portfolio[t]['Nome'][:20], line=dict(width=1.5), opacity=0.6))
            fig.update_layout(template="plotly_white", height=400, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)
        except: st.warning("Dati storici non disponibili")
