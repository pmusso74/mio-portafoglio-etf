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

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0.0
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- CALLBACK PER AGGIORNAMENTO ISTANTANEO PESI ---
def sync_weight(ticker):
    st.session_state.portfolio[ticker]['Peso'] = st.session_state[f"input_w_{ticker}"]

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

# --- AUTO UPDATE PREZZI ---
if (time.time() - st.session_state.last_update) > UPDATE_INTERVAL:
    update_all_prices()

# --- CSS PERSONALIZZATO (Incluso controllo Font Metriche) ---
st.markdown("""
    <style>
    /* Stile generale metriche */
    .stMetric { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #e0e0e0; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* MODIFICA SIZE FONT METRICHE */
    [data-testid="stMetricLabel"] {
        font-size: 1.0rem !important;
        font-weight: 600 !important;
        color: #5f6368 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        color: #1a1c1e !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.9rem !important;
    }

    /* Stile Tabella e Asset */
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
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("📁 Gestione Portafoglio")

uploaded_file = st.sidebar.file_uploader("📥 Carica Backup CSV", type="csv")
if uploaded_file:
    df_up = pd.read_csv(uploaded_file)
    new_p = {}
    for _, r in df_up.iterrows():
        t = str(r['Ticker']).upper()
        new_p[t] = {
            'Nome': r['Nome'], 'ISIN': r.get('ISIN', ''), 'Politica': r.get('Politica', 'Acc'),
            'TER': r.get('TER', '0.20%'), 'Peso': float(r['Peso']), 'Prezzo': float(r['Prezzo']),
            'Valuta': r.get('Valuta', 'EUR'), 'Cambio': 1.0, 'Investito_Reale': float(r['Investito_Reale']),
            'Quote_Reali': float(r['Quote_Reali'])
        }
    st.session_state.portfolio = new_p
    st.session_state.total_budget = float(df_up['Total_Budget'].iloc[0])

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0)

col_s1, col_s2 = st.sidebar.columns(2)
if col_s1.button("💾 SALVA", use_container_width=True):
    pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()]).to_csv(DB_FILE, index=False)
    st.sidebar.success("Salvato!")

if col_s2.button("🔄 AGGIORNA", use_container_width=True):
    update_all_prices(); st.rerun()

if st.sidebar.button("🧹 RESET DATI REALI", use_container_width=True):
    for t in st.session_state.portfolio:
        st.session_state.portfolio[t]['Investito_Reale'] = 0.0
        st.session_state.portfolio[t]['Quote_Reali'] = 0.0
    st.rerun()

with st.sidebar.expander("➕ Aggiungi ETF"):
    new_t = st.text_input("Ticker Yahoo").strip().upper()
    if st.button("Aggiungi"):
        try:
            y = yf.Ticker(new_t); i = y.info; n = i.get('shortName', new_t)
            st.session_state.portfolio[new_t] = {
                'Nome': n, 'ISIN': i.get('underlyingSymbol') or (y.isin if hasattr(y, 'isin') else ""),
                'Politica': detect_policy(i, n), 'TER': '0.20%', 'Peso': 0.0,
                'Prezzo': i.get('currentPrice') or i.get('regularMarketPrice'),
                'Valuta': i.get('currency', 'EUR'), 'Cambio': 1.0, 'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            st.rerun()
        except: st.error("Errore ticker")

# --- MAIN ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("👋 Benvenuto! Carica un file o aggiungi un ETF per iniziare.")
else:
    # Somma Pesi
    somma_pesi = sum(a['Peso'] for a in st.session_state.portfolio.values())
    if somma_pesi != 100:
        st.markdown(f"⚠️ <span class='weight-warning'>Somma pesi attuale: {somma_pesi}% (Deve essere 100%)</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"✅ <span class='weight-ok'>Somma pesi corretta: {somma_pesi}%</span>", unsafe_allow_html=True)

    # Tabella
    h = st.columns([2.2, 0.6, 0.7, 0.7, 0.9, 0.9, 0.7, 1.2])
    for col, text in zip(h, ["Asset", "Tipo", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Drift", "Azioni"]): col.write(f"**{text}**")

    total_val_portafoglio = sum(a['Quote_Reali'] * a['Prezzo'] for a in st.session_state.portfolio.values())
    
    for ticker, asset in list(st.session_state.portfolio.items()):
        p_eur = asset['Prezzo']
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.2, 0.6, 0.7, 0.7, 0.9, 0.9, 0.7, 1.2])
        with c2: st.markdown(f"<span class='tipo-tag {'acc-tag' if asset['Politica']=='Acc' else 'dist-tag'}'>{asset['Politica']}</span>", unsafe_allow_html=True)
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:35]}</div><div class='ticker-label'>{ticker}</div>", unsafe_allow_html=True)
            v_att = asset['Quote_Reali'] * p_eur
            if v_att > 0: st.markdown(f"<div class='real-status'>Valore: {v_att:,.2f}€</div>", unsafe_allow_html=True)
            isin_to_use = asset.get('ISIN', '')
            just_etf_url = f"https://www.justetf.com/it/etf-profile.html?isin={isin_to_use}" if len(str(isin_to_use)) > 5 else f"https://www.justetf.com/it/find-etf.html?query={ticker.split('.')[0]}"
            st.markdown(f"<a href='{just_etf_url}' target='_blank' class='just-link-btn'>JustETF ↗</a>", unsafe_allow_html=True)

        c3.write(f"{p_eur:,.2f}")
        c4.number_input("%", 0, 100, int(asset['Peso']), key=f"input_w_{ticker}", on_change=sync_weight, args=(ticker,), label_visibility="collapsed")
        
        target_eur = (asset['Peso'] / 100) * st.session_state.total_budget
        target_sett = target_eur / 4.33
        c5.write(f"**{target_eur:,.2f}**")
        c6.write(f"{target_sett:,.2f}")
        
        with c7:
            if total_val_portafoglio > 0:
                drift = ((v_att / total_val_portafoglio) * 100) - asset['Peso']
                st.write(f"{drift:+.1f}%")
            else: st.write("-")

        with c8:
            act1, act2, act3 = st.columns(3)
            if act1.button("➕", key=f"add_{ticker}"):
                asset['Investito_Reale'] += target_eur
                asset['Quote_Reali'] += (target_eur / p_eur) if p_eur > 0 else 0
                st.rerun()
            if act2.button("➖", key=f"sub_{ticker}"):
                if asset['Investito_Reale'] >= target_eur:
                    asset['Investito_Reale'] -= target_eur
                    asset['Quote_Reali'] = max(0.0, asset['Quote_Reali'] - (target_eur / p_eur))
                    st.rerun()
            if act3.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; st.rerun()

    # --- RIEPILOGO INVESTIMENTO ---
    st.markdown("---")
    tot_inv_reale = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_inv_reale:,.2f} €")
    m2.metric("Valore Attuale", f"{total_val_portafoglio:,.2f} €")
    m3.metric("Profit/Loss", f"{total_val_portafoglio - tot_inv_reale:,.2f} €", f"{((total_val_portafoglio/tot_inv_reale)-1)*100 if tot_inv_reale>0 else 0:+.2f}%")

    # --- ANALISI STATO E TORTA ---
    st.markdown("---")
    c_info, c_pie = st.columns([1, 1.5])
    with c_info:
        st.subheader("🏦 Stato dell'Investimento")
        st.markdown("<div class='budget-box'>", unsafe_allow_html=True)
        st.write(f"**Budget Mensile PAC:** {st.session_state.total_budget:,.2f} €")
        rapp = tot_inv_reale / st.session_state.total_budget if st.session_state.total_budget > 0 else 0
        st.write(f"**Copertura Piano:** {rapp:.1f} mensilità.")
        st.progress(min(rapp / 24, 1.0))
        st.markdown("</div>", unsafe_allow_html=True)
    with c_pie:
        if total_val_portafoglio > 0:
            df_pie = pd.DataFrame([{'Asset': a['Nome'], 'Valore': a['Quote_Reali'] * a['Prezzo']} for a in st.session_state.portfolio.values() if a['Quote_Reali'] > 0])
            st.plotly_chart(px.pie(df_pie, values='Valore', names='Asset', hole=0.4, title="Distribuzione Reale (€)"), use_container_width=True)

    # --- PERFORMANCE (SOLO ASSET CON PESO > 0) ---
    active_tks = [t for t in st.session_state.portfolio.keys() if st.session_state.portfolio[t]['Peso'] > 0]
    if active_tks:
        st.markdown("---")
        st.subheader("📊 Metriche Performance PAC (Asset Attivi > 0%)")
        try:
            data = yf.download(active_tks, period="1y", progress=False)['Close']
            if len(active_tks) == 1: data = data.to_frame(); data.columns = active_tks
            data = data.ffill().dropna()
            norm = (data / data.iloc[0]) * 100
            
            ret1y = ((data.iloc[-1] / data.iloc[0]) - 1) * 100
            ret6m = ((data.iloc[-1] / data.iloc[len(data)//2]) - 1) * 100
            
            pesi_att = [st.session_state.portfolio[t]['Peso'] for t in active_tks]
            s_p = sum(pesi_att)
            p_perf1y = sum(ret1y[t] * (st.session_state.portfolio[t]['Peso'] / s_p) for t in active_tks)
            p_perf6m = sum(ret6m[t] * (st.session_state.portfolio[t]['Peso'] / s_p) for t in active_tks)
            
            best_t = ret1y.idxmax()
            
            pc1, pc2, pc3 = st.columns(3)
            pc1.metric("Rendimento PAC (1 Anno)", f"{p_perf1y:+.2f}%")
            pc2.metric("Rendimento PAC (6 Mesi)", f"{p_perf6m:+.2f}%")
            pc3.metric("Miglior Asset (1 Anno)", f"{st.session_state.portfolio[best_t]['Nome'][:20]}...", f"{ret1y.max():+.2f}%")

            st.subheader("📈 Performance Storica (Asset Attivi)")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=norm.index, y=(norm * pesi_att).sum(axis=1)/s_p, name="⭐ IL TUO PAC", line=dict(color='red', width=4), zorder=10))
            for t in active_tks:
                fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=st.session_state.portfolio[t]['Nome'][:20], line=dict(width=1.5), opacity=0.6))
            fig.update_layout(template="plotly_white", height=400, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)
        except: st.warning("Dati storici non disponibili.")

st.sidebar.caption(f"Ultimo agg: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))}")
