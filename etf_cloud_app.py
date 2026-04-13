import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time
from datetime import datetime, timedelta

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner Pro", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv"
UPDATE_INTERVAL = 60 # Secondi tra aggiornamenti

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
    with st.spinner("Aggiornamento prezzi in corso..."):
        for ticker in list(st.session_state.portfolio.keys()):
            try:
                y = yf.Ticker(ticker); i = y.info
                p = i.get('currentPrice') or i.get('regularMarketPrice')
                if p:
                    st.session_state.portfolio[ticker]['Prezzo'] = float(p)
                    st.session_state.portfolio[ticker]['Politica'] = detect_policy(i, st.session_state.portfolio[ticker]['Nome'])
            except: continue
        st.session_state.last_update = time.time()

def load_from_dataframe(df):
    try:
        new_port = {}
        for _, r in df.iterrows():
            ticker = str(r['Ticker']).upper()
            new_port[ticker] = {
                'Nome': r['Nome'], 'ISIN': r.get('ISIN', ''), 'Politica': r.get('Politica', 'Acc'),
                'TER': r.get('TER', '0.20%'), 'Peso': float(r['Peso']), 'Prezzo': float(r['Prezzo']),
                'PrevClose': float(r.get('PrevClose', r['Prezzo'])), 'Valuta': r.get('Valuta', 'EUR'),
                'Cambio': float(r.get('Cambio', 1.0)), 'Investito_Reale': float(r['Investito_Reale']),
                'Quote_Reali': float(r['Quote_Reali'])
            }
        st.session_state.portfolio = new_port
        st.session_state.total_budget = float(df['Total_Budget'].iloc[0])
        st.success("Portafoglio caricato!")
    except Exception as e:
        st.error(f"Errore nel caricamento del file: {e}")

# --- LOGICA AUTO-UPDATE ---
next_update_time = st.session_state.last_update + UPDATE_INTERVAL
if time.time() > next_update_time:
    update_all_prices()
    st.rerun()

# --- CSS ESTETICA ---
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
    .budget-box { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #1a73e8; }
    .timer-box { color: #d32f2f; font-weight: bold; font-size: 0.85rem; padding: 5px; background: #fff5f5; border-radius: 5px; text-align: center; border: 1px solid #feb2b2; margin-top: 10px;}
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("📊 Gestione Portafoglio")

# Caricamento Manuale Ticker
with st.sidebar.expander("➕ Aggiungi ETF", expanded=False):
    new_t = st.text_input("Ticker Yahoo (es. SWDA.MI)").strip().upper()
    if st.button("Aggiungi", use_container_width=True):
        try:
            y = yf.Ticker(new_t); i = y.info; n = i.get('shortName', new_t)
            st.session_state.portfolio[new_t] = {
                'Nome': n, 'ISIN': i.get('underlyingSymbol') or (y.isin if hasattr(y, 'isin') else ""),
                'Politica': detect_policy(i, n), 'TER': '0.20%', 'Peso': 0.0,
                'Prezzo': i.get('currentPrice') or i.get('regularMarketPrice'),
                'PrevClose': i.get('previousClose', 0), 'Valuta': i.get('currency', 'EUR'),
                'Cambio': 1.0, 'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            st.rerun()
        except: st.error("Ticker non trovato")

# Caricamento CSV
st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("📥 Carica Portafoglio (CSV)", type="csv")
if uploaded_file is not None:
    load_from_dataframe(pd.read_csv(uploaded_file))

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0)

# Pulsanti Azione
c_save, c_upd = st.sidebar.columns(2)
if c_save.button("💾 SALVA", use_container_width=True):
    df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
    df_save.to_csv(DB_FILE, index=False)
    st.sidebar.success("Salvato!")

if c_upd.button("🔄 AGGIORNA", use_container_width=True):
    update_all_prices()
    st.rerun()

# Timer Visibile
next_dt = datetime.fromtimestamp(next_update_time).strftime('%H:%M:%S')
st.sidebar.markdown(f"<div class='timer-box'>⏱ Prossimo aggiornamento: {next_dt}</div>", unsafe_allow_html=True)

# --- MAIN ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("Benvenuto! Aggiungi un ETF o carica un file CSV dal menu a sinistra.")
else:
    # Tabella principale
    h = st.columns([2.5, 0.6, 0.8, 0.8, 1, 1, 1.2])
    for col, text in zip(h, ["Asset", "Tipo", "Prezzo €", "Peso %", "Mensile €", "Drift", "Azioni"]): col.write(f"**{text}**")

    total_val_portafoglio = sum(a['Quote_Reali'] * a['Prezzo'] * a['Cambio'] for a in st.session_state.portfolio.values())
    
    for ticker, asset in list(st.session_state.portfolio.items()):
        p_eur = asset['Prezzo'] * asset['Cambio']
        target_eur = (asset['Peso'] / 100) * st.session_state.total_budget
        v_attuale = asset['Quote_Reali'] * p_eur
        
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2.5, 0.6, 0.8, 0.8, 1, 1, 1.2])
        with c2: st.markdown(f"<span class='tipo-tag {'acc-tag' if asset['Politica']=='Acc' else 'dist-tag'}'>{asset['Politica']}</span>", unsafe_allow_html=True)
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:35]}</div><div class='ticker-label'>{ticker}</div>", unsafe_allow_html=True)
            if v_attuale > 0: st.markdown(f"<div class='real-status'>Posseduto: {v_attuale:,.2f}€</div>", unsafe_allow_html=True)
            if asset.get('ISIN'): st.markdown(f"<a href='https://www.justetf.com/it/etf-profile.html?isin={asset['ISIN']}' target='_blank' class='just-link-btn'>JustETF ↗</a>", unsafe_allow_html=True)

        c3.write(f"{p_eur:,.2f}")
        asset['Peso'] = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        c5.write(f"**{target_eur:,.2f} €**")
        with c6:
            if total_val_portafoglio > 0:
                drift = ((v_attuale / total_val_portafoglio) * 100) - asset['Peso']
                st.write(f"{drift:+.1f}%")
            else: st.write("-")

        with c7:
            act1, act2, act3 = st.columns(3)
            if act1.button("➕", key=f"add_{ticker}", help="Registra acquisto quota mensile"):
                asset['Investito_Reale'] += target_eur
                asset['Quote_Reali'] += (target_eur / p_eur) if p_eur > 0 else 0
                st.rerun()
            if act2.button("➖", key=f"sub_{ticker}", help="Storna quota mensile"):
                if asset['Investito_Reale'] >= target_eur:
                    asset['Investito_Reale'] -= target_eur
                    asset['Quote_Reali'] = max(0, asset['Quote_Reali'] - (target_eur / p_eur))
                    st.rerun()
            if act3.button("🗑️", key=f"del_{ticker}", help="Rimuovi"):
                del st.session_state.portfolio[ticker]; st.rerun()

    # --- METRICHE ---
    st.markdown("---")
    tot_investito_reale = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_investito_reale:,.2f} €")
    m2.metric("Valore Portafoglio", f"{total_val_portafoglio:,.2f} €")
    m3.metric("Profit/Loss", f"{total_val_portafoglio - tot_investito_reale:,.2f} €", f"{((total_val_portafoglio/tot_investito_reale)-1)*100 if tot_investito_reale>0 else 0:+.2f}%")

    # --- GRAFICO STORICO ---
    st.subheader("📈 Performance Storica (1 Anno)")
    try:
        tks = list(st.session_state.portfolio.keys())
        data = yf.download(tks, period="1y", progress=False)['Close']
        if len(tks) == 1: data = data.to_frame(); data.columns = tks
        norm = (data.ffill() / data.ffill().iloc[0]) * 100
        fig = go.Figure()
        pesi = [st.session_state.portfolio[t]['Peso'] for t in tks]
        if sum(pesi) > 0:
            fig.add_trace(go.Scatter(x=norm.index, y=(norm * pesi).sum(axis=1)/sum(pesi), name="⭐ IL TUO PAC", line=dict(color='red', width=4), zorder=10))
        for t in tks:
            fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=st.session_state.portfolio[t]['Nome'][:20], line=dict(width=1.5), opacity=0.6))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)
    except: st.warning("Grafico non disponibile")

    # --- DISTRIBUZIONE E BUDGET ---
    st.markdown("---")
    st.subheader("📊 Analisi Portafoglio Reale")
    c_pie, c_info = st.columns([1.5, 1])
    with c_pie:
        if total_val_portafoglio > 0:
            df_pie = pd.DataFrame([{'Asset': a['Nome'], 'Valore': a['Quote_Reali'] * a['Prezzo'] * a['Cambio']} for a in st.session_state.portfolio.values() if a['Quote_Reali'] > 0])
            fig_p = px.pie(df_pie, values='Valore', names='Asset', hole=0.4)
            fig_p.update_traces(textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Valore: %{value:,.2f} €')
            fig_p.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_p, use_container_width=True)
    with c_info:
        st.markdown("<div class='budget-box'>", unsafe_allow_html=True)
        st.write("### 🏦 Riepilogo Piano")
        st.write(f"**Euro Totali Investiti:** {tot_investito_reale:,.2f} €")
        st.write(f"**Budget Mensile PAC:** {st.session_state.total_budget:,.2f} €")
        mensilita = tot_investito_reale / st.session_state.total_budget if st.session_state.total_budget > 0 else 0
        st.write(f"**Copertura:** Hai accumulato **{mensilita:.1f} mensilità**.")
        st.progress(min(mensilita / 24, 1.0), text="Progresso (Target 2 anni)")
        st.markdown("</div>", unsafe_allow_html=True)

# Questo comando mantiene l'app attiva e aggiorna la UI ogni secondo senza flicker pesanti
time.sleep(1)
st.rerun()
