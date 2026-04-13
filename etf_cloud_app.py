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
UPDATE_INTERVAL = 60  # Aggiornamento ogni 60 secondi

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

def load_from_dataframe(df):
    try:
        new_port = {}
        for _, r in df.iterrows():
            t = str(r['Ticker']).upper()
            new_port[t] = {
                'Nome': r['Nome'], 'ISIN': r.get('ISIN', ''), 'Politica': r.get('Politica', 'Acc'),
                'TER': r.get('TER', '0.20%'), 'Peso': float(r['Peso']), 'Prezzo': float(r['Prezzo']),
                'PrevClose': float(r.get('PrevClose', r['Prezzo'])), 'Valuta': r.get('Valuta', 'EUR'),
                'Cambio': float(r.get('Cambio', 1.0)), 'Investito_Reale': float(r['Investito_Reale']),
                'Quote_Reali': float(r['Quote_Reali'])
            }
        st.session_state.portfolio = new_port
        st.session_state.total_budget = float(df['Total_Budget'].iloc[0])
        st.success("Portafoglio caricato con successo!")
    except:
        st.error("Errore nel formato del file CSV.")

# --- LOGICA AUTO-REFRESH (SENZA SFARFALLIO CONTINUO) ---
# L'app fa il rerun solo quando scatta il minuto, non ogni secondo
if (time.time() - st.session_state.last_update) > UPDATE_INTERVAL:
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
    .timer-info { font-size: 0.8rem; color: #d32f2f; font-weight: bold; background: #fff5f5; padding: 8px; border-radius: 5px; border: 1px solid #feb2b2; text-align: center; }
    .budget-box { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1a73e8; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("📁 Portafoglio")

# Caricamento CSV
uploaded_file = st.sidebar.file_uploader("📥 Carica file PAC (.csv)", type="csv", help="Carica un file salvato precedentemente per ripristinare i dati.")
if uploaded_file:
    load_from_dataframe(pd.read_csv(uploaded_file))

with st.sidebar.expander("➕ Aggiungi Nuovo ETF"):
    new_t = st.text_input("Ticker Yahoo (es. SWDA.MI)").strip().upper()
    if st.button("Aggiungi all'elenco", use_container_width=True):
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
        except: st.error("Ticker non trovato.")

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0, help="Cifra che investi ogni mese.")

col_s1, col_s2 = st.sidebar.columns(2)
if col_s1.button("💾 SALVA", use_container_width=True, help="Salva permanentemente i pesi e le quote reali."):
    pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()]).to_csv(DB_FILE, index=False)
    st.sidebar.success("Salvato!")
if col_s2.button("🔄 AGGIORNA", use_container_width=True, help="Forza l'aggiornamento immediato dei prezzi."):
    update_all_prices(); st.rerun()

# Timer Visibile (statico, si aggiorna solo al refresh)
last_str = datetime.fromtimestamp(st.session_state.last_update).strftime('%H:%M:%S')
next_str = datetime.fromtimestamp(st.session_state.last_update + UPDATE_INTERVAL).strftime('%H:%M:%S')
st.sidebar.markdown(f"""
<div class='timer-info'>
    ⏱ Ultimo aggiornamento: {last_str}<br>
    🔄 Prossimo aggiornamento: {next_str}
</div>
""", unsafe_allow_html=True)

# --- MAIN INTERFACE ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("Benvenuto! Carica un file CSV o aggiungi un ETF dal menu a sinistra.")
else:
    # Tabella
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

        c3.write(f"{p_eur:,.2f}")
        asset['Peso'] = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed", help="Peso percentuale nel portafoglio.")
        c5.write(f"**{target_eur:,.2f} €**")
        with c6:
            if total_val_portafoglio > 0:
                drift = ((v_attuale / total_val_portafoglio) * 100) - asset['Peso']
                st.write(f"{drift:+.1f}%")
            else: st.write("-")

        with c7:
            a1, a2, a3 = st.columns(3)
            if a1.button("➕", key=f"add_{ticker}", help="REGISTRA ACQUISTO: Aggiunge la quota target al posseduto reale."):
                asset['Investito_Reale'] += target_eur
                asset['Quote_Reali'] += (target_eur / p_eur) if p_eur > 0 else 0
                st.rerun()
            if a2.button("➖", key=f"sub_{ticker}", help="STORNA: Sottrae una quota target (utile per correggere errori)."):
                if asset['Investito_Reale'] >= target_eur:
                    asset['Investito_Reale'] -= target_eur
                    asset['Quote_Reali'] = max(0, asset['Quote_Reali'] - (target_eur / p_eur))
                    st.rerun()
            if a3.button("🗑️", key=f"del_{ticker}", help="ELIMINA: Rimuove l'asset dal piano."):
                del st.session_state.portfolio[ticker]; st.rerun()

    # --- METRICHE ---
    st.markdown("---")
    tot_investito_reale = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_investito_reale:,.2f} €", help="Totale euro spesi per gli acquisti.")
    m2.metric("Valore Attuale", f"{total_val_portafoglio:,.2f} €", help="Valore di mercato odierno.")
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
    except: st.warning("Dati storici non disponibili.")

    # --- ALLOCAZIONE E BUDGET ---
    st.markdown("---")
    c_pie, c_info = st.columns([1.5, 1])
    with c_pie:
        st.subheader("📊 Distribuzione Reale (€)")
        if total_val_portafoglio > 0:
            df_pie = pd.DataFrame([{'Asset': a['Nome'], 'Valore': a['Quote_Reali'] * a['Prezzo'] * a['Cambio']} for a in st.session_state.portfolio.values() if a['Quote_Reali'] > 0])
            fig_p = px.pie(df_pie, values='Valore', names='Asset', hole=0.4)
            fig_p.update_traces(textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Valore: %{value:,.2f} €')
            fig_p.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_p, use_container_width=True)

    with c_info:
        st.subheader("🏦 Riepilogo Piano")
        st.markdown("<div class='budget-box'>", unsafe_allow_html=True)
        st.write(f"**Investimento Totale:** {tot_investito_reale:,.2f} €")
        st.write(f"**Budget Mensile PAC:** {st.session_state.total_budget:,.2f} €")
        mensilita = tot_investito_reale / st.session_state.total_budget if st.session_state.total_budget > 0 else 0
        st.write(f"**Copertura:** Hai investito circa **{mensilita:.1f} mensilità**.")
        st.progress(min(mensilita / 24, 1.0), text="Progresso (Target 2 anni)")
        st.markdown("</div>", unsafe_allow_html=True)
