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
            p = i.get('currentPrice') or i.get('regularMarketPrice') or i.get('previousClose')
            if p:
                st.session_state.portfolio[ticker]['Prezzo'] = float(p)
                st.session_state.portfolio[ticker]['Politica'] = detect_policy(i, st.session_state.portfolio[ticker]['Nome'])
        except: continue
    st.session_state.last_update = time.time()

def load_from_dataframe(df):
    try:
        new_port = {}
        for _, r in df.iterrows():
            t = str(r['Ticker']).upper()
            new_port[t] = {
                'Nome': r['Nome'], 'ISIN': r.get('ISIN', ''), 'Politica': r.get('Politica', 'Acc'),
                'TER': r.get('TER', '0.20%'), 'Peso': float(r['Peso']), 'Prezzo': float(r['Prezzo']),
                'Valuta': r.get('Valuta', 'EUR'), 'Cambio': float(r.get('Cambio', 1.0)),
                'Investito_Reale': float(r['Investito_Reale']), 'Quote_Reali': float(r['Quote_Reali'])
            }
        st.session_state.portfolio = new_port
        st.session_state.total_budget = float(df['Total_Budget'].iloc[0])
        st.toast("✅ Portafoglio caricato!")
    except: st.error("Errore CSV")

# --- AUTO-REFRESH ---
if (time.time() - st.session_state.last_update) > UPDATE_INTERVAL:
    update_all_prices()

# --- CSS ESTETICA ---
st.markdown("""
    <style>
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 1.0rem; line-height: 1.1; }
    .ticker-label { color: #d32f2f; font-weight: bold; font-family: monospace; font-size: 0.8rem; }
    .real-status { color: #2e7d32; font-size: 0.85rem; font-weight: 700; background: #f0f7f0; padding: 2px 6px; border-radius: 4px; margin-top: 4px; display: inline-block; }
    .just-link-btn { display: inline-block; margin-top: 6px; padding: 3px 10px; background-color: #ffffff; color: #1a73e8 !important; text-decoration: none !important; border: 1px solid #1a73e8; border-radius: 15px; font-size: 0.65rem; font-weight: 700; }
    .just-link-btn:hover { background-color: #1a73e8; color: white !important; }
    .tipo-tag { padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white; }
    .acc-tag { background-color: #1a73e8; } .dist-tag { background-color: #f29900; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("📁 Gestione Portafoglio")
uploaded_file = st.sidebar.file_uploader("📥 Carica Backup CSV", type="csv")
if uploaded_file:
    load_from_dataframe(pd.read_csv(uploaded_file))

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0)

col_s1, col_s2 = st.sidebar.columns(2)
if col_s1.button("💾 SALVA", use_container_width=True):
    pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()]).to_csv(DB_FILE, index=False)
    st.sidebar.success("Salvato!")
if col_s2.button("🔄 AGGIORNA", use_container_width=True):
    update_all_prices(); st.rerun()

with st.sidebar.expander("➕ Aggiungi ETF"):
    nt = st.text_input("Ticker Yahoo (es. SWDA.MI)").strip().upper()
    if st.button("Conferma"):
        try:
            y = yf.Ticker(nt); i = y.info
            st.session_state.portfolio[nt] = {
                'Nome': i.get('shortName', nt), 
                'ISIN': i.get('underlyingSymbol') or (y.isin if hasattr(y, 'isin') else ""),
                'Politica': detect_policy(i, i.get('shortName', nt)), 'Peso': 0.0, 
                'Prezzo': float(i.get('currentPrice') or i.get('regularMarketPrice')),
                'Valuta': i.get('currency', 'EUR'), 'Cambio': 1.0, 'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            st.rerun()
        except: st.error("Ticker non trovato")

# --- MAIN ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("👋 Benvenuto! Carica un file o aggiungi un ETF per iniziare.")
else:
    # Tabella
    h = st.columns([2.5, 0.6, 0.7, 0.7, 0.9, 0.9, 0.8, 1.2])
    labels = ["Asset / JustETF", "Tipo", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Quote S.", "Azioni"]
    for col, lab in zip(h, labels): col.write(f"**{lab}**")

    total_val_port = sum(v['Quote_Reali'] * v['Prezzo'] * v.get('Cambio', 1.0) for v in st.session_state.portfolio.values())

    for ticker, asset in st.session_state.portfolio.items():
        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.5, 0.6, 0.7, 0.7, 0.9, 0.9, 0.8, 1.2])
        
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:35]}</div><div class='ticker-label'>{ticker}</div>", unsafe_allow_html=True)
            v_reale_asset = asset['Quote_Reali'] * p_eur
            if asset['Quote_Reali'] > 0:
                st.markdown(f"<div class='real-status'>Posseduto: {v_reale_asset:,.2f} €</div>", unsafe_allow_html=True)
            
            # --- LOGICA LINK JUSTETF (RIPRISTINATA E BLOCCATA) ---
            isin = asset.get('ISIN')
            if isin and len(str(isin)) > 5:
                l_url = f"https://www.justetf.com/it/etf-profile.html?isin={isin}"
            else:
                l_url = f"https://www.justetf.com/it/find-etf.html?query={ticker.split('.')[0]}"
            st.markdown(f"<a href='{l_url}' target='_blank' class='just-link-btn'>JustETF ↗</a>", unsafe_allow_html=True)

        with c2: st.markdown(f"<span class='tipo-tag {'acc-tag' if asset['Politica']=='Acc' else 'dist-tag'}'>{asset['Politica']}</span>", unsafe_allow_html=True)
        c3.write(f"{p_eur:,.2f}")
        
        asset['Peso'] = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        
        inv_m = (asset['Peso'] / 100) * st.session_state.total_budget
        inv_w = inv_m / 4.33
        quote_w = inv_w / p_eur if p_eur > 0 else 0
        
        c5.write(f"{inv_m:,.2f}")
        c6.write(f"**{inv_w:,.2f}**")
        c7.write(f"{quote_w:.3f}")

        with c8:
            a1, a2, a3 = st.columns(3)
            if a1.button("➕", key=f"add_{ticker}"):
                st.session_state.portfolio[ticker]['Investito_Reale'] += inv_w
                st.session_state.portfolio[ticker]['Quote_Reali'] += quote_w
                st.rerun()
            if a2.button("➖", key=f"sub_{ticker}"):
                if st.session_state.portfolio[ticker]['Investito_Reale'] >= inv_w:
                    st.session_state.portfolio[ticker]['Investito_Reale'] -= inv_w
                    st.session_state.portfolio[ticker]['Quote_Reali'] = max(0.0, st.session_state.portfolio[ticker]['Quote_Reali'] - quote_w)
                    st.rerun()
            if a3.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; st.rerun()

    # --- RIEPILOGO E GRAFICI ---
    st.markdown("---")
    tot_inv = sum(v['Investito_Reale'] for v in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_inv:,.2f} €")
    m2.metric("Valore Attuale", f"{total_val_port:,.2f} €")
    m3.metric("Profit/Loss", f"{total_val_port - tot_inv:,.2f} €", f"{((total_val_port/tot_inv)-1)*100 if tot_inv>0 else 0:+.2f}%")

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
        fig.update_layout(template="plotly_white", height=380, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)
    except: pass

    st.markdown("---")
    c_pie, c_info = st.columns([1.5, 1])
    with c_pie:
        st.subheader("📊 Distribuzione Reale")
        pie_data = [{'Asset': v['Nome'], 'Valore': v['Quote_Reali'] * v['Prezzo']} for v in st.session_state.portfolio.values() if v['Quote_Reali'] > 0]
        if pie_data:
            st.plotly_chart(px.pie(pd.DataFrame(pie_data), values='Valore', names='Asset', hole=0.4), use_container_width=True)
    with c_info:
        st.write("### 🏦 Riepilogo Piano")
        mens = tot_inv / st.session_state.total_budget if st.session_state.total_budget > 0 else 0
        st.write(f"**Mensilità accumulate:** {mens:.1f}")
        st.progress(min(mens / 24, 1.0))

st.sidebar.caption(f"Ultimo agg: {datetime.fromtimestamp(st.session_state.last_update).strftime('%H:%M:%S')}")
