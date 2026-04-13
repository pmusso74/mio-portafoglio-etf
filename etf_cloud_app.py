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
UPDATE_INTERVAL = 60 

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- FUNZIONI DI SUPPORTO ---
def detect_policy(inf, nome):
    y_val = inf.get('dividendYield') or inf.get('trailingAnnualDividendYield') or 0
    return "Dist" if y_val > 0 or "dist" in nome.lower() else "Acc"

def update_all_prices():
    if not st.session_state.portfolio: return
    for ticker in list(st.session_state.portfolio.keys()):
        try:
            y = yf.Ticker(ticker); i = y.info
            p = i.get('currentPrice') or i.get('regularMarketPrice')
            if p:
                st.session_state.portfolio[ticker]['Prezzo'] = float(p)
                st.session_state.portfolio[ticker]['Politica'] = detect_policy(i, st.session_state.portfolio[ticker]['Nome'])
        except: continue
    st.session_state.last_update = time.time()

# --- LOGICA AUTO-REFRESH ---
if (time.time() - st.session_state.last_update) > UPDATE_INTERVAL:
    update_all_prices()
    st.rerun()

# --- CSS ESTETICA ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #eee; }
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 0.9rem; line-height: 1.1; }
    .ticker-label { color: #666; font-family: monospace; font-size: 0.75rem; }
    .tipo-tag { padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white; }
    .acc-tag { background-color: #1a73e8; }
    .dist-tag { background-color: #f29900; }
    .real-status { color: #2e7d32; font-size: 0.75rem; font-weight: 700; background: #e8f5e9; padding: 2px 5px; border-radius: 4px; display: inline-block; margin-top: 3px;}
    .just-link-btn { display: inline-block; margin-top: 5px; padding: 2px 8px; background-color: #ffffff; color: #1a73e8 !important; text-decoration: none !important; border: 1px solid #1a73e8; border-radius: 4px; font-size: 0.6rem; font-weight: 700; }
    .budget-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1a73e8; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("📁 Portafoglio")
uploaded_file = st.sidebar.file_uploader("📥 Carica Backup CSV", type="csv")
if uploaded_file:
    df_upload = pd.read_csv(uploaded_file)
    for _, r in df_upload.iterrows():
        t = str(r['Ticker']).upper()
        st.session_state.portfolio[t] = {
            'Nome': r['Nome'], 'ISIN': r.get('ISIN', ''), 'Politica': r.get('Politica', 'Acc'),
            'TER': r.get('TER', '0.20%'), 'Peso': float(r['Peso']), 'Prezzo': float(r['Prezzo']),
            'Valuta': r.get('Valuta', 'EUR'), 'Cambio': float(r.get('Cambio', 1.0)),
            'Investito_Reale': float(r['Investito_Reale']), 'Quote_Reali': float(r['Quote_Reali'])
        }
    st.session_state.total_budget = float(df_upload['Total_Budget'].iloc[0])

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0)

col_b1, col_b2 = st.sidebar.columns(2)
if col_b1.button("💾 SALVA", use_container_width=True):
    pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()]).to_csv(DB_FILE, index=False)
    st.sidebar.success("Salvato!")

if col_b2.button("🔄 AGGIORNA", use_container_width=True):
    update_all_prices(); st.rerun()

with st.sidebar.expander("➕ Aggiungi ETF"):
    new_t = st.text_input("Ticker Yahoo").strip().upper()
    if st.button("Conferma"):
        try:
            y = yf.Ticker(new_t); i = y.info; n = i.get('shortName', new_t)
            st.session_state.portfolio[new_t] = {
                'Nome': n, 'ISIN': i.get('underlyingSymbol') or (y.isin if hasattr(y, 'isin') else ""),
                'Politica': detect_policy(i, n), 'TER': '0.20%', 'Peso': 0.0,
                'Prezzo': i.get('currentPrice') or i.get('regularMarketPrice'),
                'Valuta': i.get('currency', 'EUR'), 'Cambio': 1.0, 'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            st.rerun()
        except: st.error("Errore")

# --- MAIN ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("👋 Carica un file o aggiungi un ETF.")
else:
    # Tabella
    h = st.columns([2.2, 0.6, 0.7, 0.7, 0.9, 0.9, 0.8, 1.2])
    cols_labels = ["Asset", "Tipo", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Quote S.", "Azioni"]
    for col, text in zip(h, cols_labels): col.write(f"**{text}**")

    total_val_port = sum(a['Quote_Reali'] * a['Prezzo'] * a.get('Cambio', 1.0) for a in st.session_state.portfolio.values())
    
    for ticker, asset in st.session_state.portfolio.items():
        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.2, 0.6, 0.7, 0.7, 0.9, 0.9, 0.8, 1.2])
        
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:30]}</div><div class='ticker-label'>{ticker}</div>", unsafe_allow_html=True)
            v_reale = asset['Quote_Reali'] * p_eur
            if asset['Quote_Reali'] > 0: st.markdown(f"<div class='real-status'>{v_reale:,.2f}€</div>", unsafe_allow_html=True)
            if asset.get('ISIN'): st.markdown(f"<a href='https://www.justetf.com/it/etf-profile.html?isin={asset['ISIN']}' target='_blank' class='just-link-btn'>JustETF</a>", unsafe_allow_html=True)

        with c2: st.markdown(f"<span class='tipo-tag {'acc-tag' if asset['Politica']=='Acc' else 'dist-tag'}'>{asset['Politica']}</span>", unsafe_allow_html=True)
        c3.write(f"{p_eur:,.2f}")
        
        # INPUT PESO
        asset['Peso'] = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        
        # CALCOLI BUDGET
        inv_m = (asset['Peso'] / 100) * st.session_state.total_budget
        inv_w = inv_m / 4.33
        quote_w = inv_w / p_eur if p_eur > 0 else 0
        
        c5.write(f"{inv_m:,.2f}")
        c6.write(f"**{inv_w:,.2f}**")
        c7.write(f"{quote_w:.3f}")

        with c8:
            a1, a2, a3 = st.columns(3)
            # LOGICA PULSANTI (Uso diretto dei valori ricalcolati)
            if a1.button("➕", key=f"add_{ticker}"):
                st.session_state.portfolio[ticker]['Investito_Reale'] += inv_w
                st.session_state.portfolio[ticker]['Quote_Reali'] += quote_w
                st.toast(f"Registrato acquisto {ticker}")
                st.rerun()
            
            if a2.button("➖", key=f"sub_{ticker}"):
                if st.session_state.portfolio[ticker]['Investito_Reale'] >= inv_w:
                    st.session_state.portfolio[ticker]['Investito_Reale'] -= inv_w
                    st.session_state.portfolio[ticker]['Quote_Reali'] = max(0.0, st.session_state.portfolio[ticker]['Quote_Reali'] - quote_w)
                    st.rerun()

            if a3.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; st.rerun()

    # --- METRICHE E GRAFICI ---
    st.markdown("---")
    tot_inv = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Investito", f"{tot_inv:,.2f} €")
    m2.metric("Valore Attuale", f"{total_val_port:,.2f} €")
    m3.metric("P&L", f"{total_val_port - tot_inv:,.2f} €", f"{((total_val_port/tot_inv)-1)*100 if tot_inv>0 else 0:+.2f}%")

    # Grafico Storico
    try:
        tks = list(st.session_state.portfolio.keys())
        data = yf.download(tks, period="1y", progress=False)['Close']
        if len(tks) == 1: data = data.to_frame(); data.columns = tks
        norm = (data.ffill() / data.ffill().iloc[0]) * 100
        fig = go.Figure()
        pesi = [st.session_state.portfolio[t]['Peso'] for t in tks]
        if sum(pesi) > 0:
            fig.add_trace(go.Scatter(x=norm.index, y=(norm * pesi).sum(axis=1)/sum(pesi), name="⭐ IL TUO PAC", line=dict(color='red', width=4)))
        for t in tks:
            fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=st.session_state.portfolio[t]['Nome'][:20], line=dict(width=1.2), opacity=0.5))
        fig.update_layout(template="plotly_white", height=380, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)
    except: pass

    # Distribuzione
    st.markdown("---")
    c_pie, c_info = st.columns([1.5, 1])
    with c_pie:
        if total_val_port > 0:
            df_pie = pd.DataFrame([{'Asset': a['Nome'], 'Valore': a['Quote_Reali'] * a['Prezzo']} for a in st.session_state.portfolio.values() if a['Quote_Reali'] > 0])
            fig_p = px.pie(df_pie, values='Valore', names='Asset', hole=0.4)
            fig_p.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_p, use_container_width=True)
    with c_info:
        st.markdown("<div class='budget-box'>", unsafe_allow_html=True)
        st.write("### 🏦 Riepilogo")
        st.write(f"**Versato:** {tot_inv:,.2f} €")
        mens = tot_inv / st.session_state.total_budget if st.session_state.total_budget > 0 else 0
        st.write(f"**Mensilità accumulate:** {mens:.1f}")
        st.progress(min(mens / 24, 1.0))
        st.markdown("</div>", unsafe_allow_html=True)

st.sidebar.caption(f"Ultimo agg: {datetime.fromtimestamp(st.session_state.last_update).strftime('%H:%M:%S')}")
