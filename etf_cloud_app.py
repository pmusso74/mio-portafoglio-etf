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
def update_all_prices():
    if not st.session_state.portfolio: return
    with st.spinner("Aggiornamento prezzi..."):
        for ticker in list(st.session_state.portfolio.keys()):
            try:
                y = yf.Ticker(ticker); i = y.info
                p = i.get('currentPrice') or i.get('regularMarketPrice') or i.get('previousClose')
                if p:
                    st.session_state.portfolio[ticker]['Prezzo'] = float(p)
                    # Cambio Valuta semplificato
                    st.session_state.portfolio[ticker]['Cambio'] = 1.0 
            except: continue
        st.session_state.last_update = time.time()

# --- AUTO-REFRESH ---
if (time.time() - st.session_state.last_update) > UPDATE_INTERVAL:
    update_all_prices()

# --- CSS ESTETICA ---
st.markdown("""
    <style>
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 1.1rem; }
    .ticker-label { color: #d32f2f; font-weight: bold; font-family: monospace; font-size: 0.85rem; }
    .real-status { color: #2e7d32; font-size: 0.85rem; font-weight: 700; background: #f0f7f0; padding: 3px 8px; border-radius: 5px; border-left: 3px solid #2e7d32; margin-top: 5px; }
    .just-link-btn { display: inline-block; margin-top: 8px; padding: 4px 12px; background-color: #ffffff; color: #1a73e8 !important; text-decoration: none !important; border: 1px solid #1a73e8; border-radius: 20px; font-size: 0.7rem; font-weight: 700; }
    .budget-box { background-color: #f0f7ff; padding: 20px; border-radius: 10px; border: 1px solid #1a73e8; }
    .tipo-tag { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; color: white; }
    .acc-tag { background-color: #1a73e8; } .dist-tag { background-color: #f29900; }
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
            'Cambio': float(r.get('Cambio', 1.0)), 'Investito_Reale': float(r['Investito_Reale']),
            'Quote_Reali': float(r['Quote_Reali'])
        }
    st.session_state.total_budget = float(df_up['Total_Budget'].iloc[0])

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0)

cs1, cs2 = st.sidebar.columns(2)
if cs1.button("💾 SALVA", use_container_width=True):
    df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
    df_save.to_csv(DB_FILE, index=False)
    st.sidebar.success("Salvato!")
if cs2.button("🔄 AGGIORNA", use_container_width=True):
    update_all_prices(); st.rerun()

with st.sidebar.expander("➕ Aggiungi ETF"):
    nt = st.text_input("Ticker Yahoo").strip().upper()
    if st.button("Aggiungi"):
        try:
            y = yf.Ticker(nt); i = y.info
            st.session_state.portfolio[nt] = {
                'Nome': i.get('shortName', nt), 'ISIN': i.get('underlyingSymbol') or nt,
                'Politica': 'Acc', 'Peso': 0.0, 'Prezzo': float(i.get('currentPrice') or i.get('regularMarketPrice')),
                'Cambio': 1.0, 'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            st.rerun()
        except: st.sidebar.error("Ticker non trovato")

# --- MAIN ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("👋 Aggiungi un ETF o carica un file per iniziare.")
else:
    # Intestazioni
    h = st.columns([2.5, 0.7, 0.8, 0.8, 1.0, 1.0, 0.8, 1.2])
    labels = ["Asset / JustETF", "Tipo", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Quote S.", "Azioni"]
    for col, lab in zip(h, labels): col.write(f"**{lab}**")

    # Calcolo totale portafoglio PRIMA del ciclo
    total_val_port = sum(v['Quote_Reali'] * v['Prezzo'] * v.get('Cambio', 1.0) for v in st.session_state.portfolio.values())

    for ticker, asset in st.session_state.portfolio.items():
        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.5, 0.7, 0.8, 0.8, 1.0, 1.0, 0.8, 1.2])
        
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:35]}</div><div class='ticker-label'>{ticker}</div>", unsafe_allow_html=True)
            v_reale_asset = asset['Quote_Reali'] * p_eur
            if asset['Quote_Reali'] > 0:
                st.markdown(f"<div class='real-status'>Posseduto: {v_reale_asset:,.2f} €</div>", unsafe_allow_html=True)
            if asset.get('ISIN'):
                st.markdown(f"<a href='https://www.justetf.com/it/etf-profile.html?isin={asset['ISIN']}' target='_blank' class='just-link-btn'>JustETF ↗</a>", unsafe_allow_html=True)

        with c2:
            st.markdown(f"<span class='tipo-tag {'acc-tag' if asset['Politica']=='Acc' else 'dist-tag'}'>{asset['Politica']}</span>", unsafe_allow_html=True)
        
        c3.write(f"{p_eur:,.2f}")
        
        # Sincronizzazione Peso
        asset['Peso'] = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        
        # Calcoli Budget
        inv_mensile = (asset['Peso'] / 100) * st.session_state.total_budget
        inv_settimana = inv_mensile / 4.33
        quote_settimana = inv_settimana / p_eur if p_eur > 0 else 0
        
        c5.write(f"{inv_mensile:,.2f}")
        c6.write(f"**{inv_settimana:,.2f}**")
        c7.write(f"{quote_settimana:.3f}")

        with c8:
            act1, act2, act3 = st.columns(3)
            if act1.button("➕", key=f"add_{ticker}"):
                st.session_state.portfolio[ticker]['Investito_Reale'] += inv_settimana
                st.session_state.portfolio[ticker]['Quote_Reali'] += quote_settimana
                st.rerun()
            if act2.button("➖", key=f"sub_{ticker}"):
                if st.session_state.portfolio[ticker]['Investito_Reale'] >= inv_settimana:
                    st.session_state.portfolio[ticker]['Investito_Reale'] -= inv_settimana
                    st.session_state.portfolio[ticker]['Quote_Reali'] = max(0.0, st.session_state.portfolio[ticker]['Quote_Reali'] - quote_settimana)
                    st.rerun()
            if act3.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; st.rerun()

    # --- RIEPILOGO ---
    st.markdown("---")
    tot_investito = sum(v['Investito_Reale'] for v in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_investito:,.2f} €")
    m2.metric("Valore Attuale", f"{total_val_port:,.2f} €")
    m3.metric("Profit/Loss", f"{total_val_port - tot_investito:,.2f} €", f"{((total_val_port/tot_investito)-1)*100 if tot_investito>0 else 0:+.2f}%")

    # --- GRAFICI ---
    st.subheader("📈 Performance Storica (1 Anno)")
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
            fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=st.session_state.portfolio[t]['Nome'][:20], line=dict(width=1.5), opacity=0.5))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)
    except: st.warning("Grafico storico non disponibile")

    # --- TORTA E BUDGET ---
    st.markdown("---")
    st.subheader("📊 Analisi Portafoglio Reale")
    c_pie, c_info = st.columns([1.5, 1])
    
    with c_pie:
        # Generazione DataFrame per la torta filtrando solo chi ha quote > 0
        pie_data = []
        for t, v in st.session_state.portfolio.items():
            if v['Quote_Reali'] > 0:
                pie_data.append({'Asset': v['Nome'], 'Valore': v['Quote_Reali'] * v['Prezzo']})
        
        if pie_data:
            df_pie = pd.DataFrame(pie_data)
            fig_p = px.pie(df_pie, values='Valore', names='Asset', hole=0.4)
            fig_p.update_traces(textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Valore: %{value:,.2f} €')
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.info("Registra un acquisto col tasto ➕ per vedere la distribuzione reale.")

    with c_info:
        st.markdown("<div class='budget-box'>", unsafe_allow_html=True)
        st.write("### 🏦 Riepilogo Piano")
        st.write(f"**Investimento Totale:** {tot_investito:,.2f} €")
        st.write(f"**Budget Mensile PAC:** {st.session_state.total_budget:,.2f} €")
        mens = tot_investito / st.session_state.total_budget if st.session_state.total_budget > 0 else 0
        st.write(f"**Copertura:** Hai accumulato **{mens:.1f} mensilità**.")
        st.progress(min(mens / 24, 1.0), text="Progresso (Target 2 anni)")
        st.markdown("</div>", unsafe_allow_html=True)

st.sidebar.caption(f"Ultimo agg: {datetime.fromtimestamp(st.session_state.last_update).strftime('%H:%M:%S')}")
