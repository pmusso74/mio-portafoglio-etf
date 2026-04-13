import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import urllib.parse
import re
import os  # Per gestire il salvataggio su disco

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="ETF PAC Planner", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv" # Nome del file di salvataggio fisso

# CSS ESTETICA
st.markdown("""
    <style>
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 1.15rem; margin-bottom: 2px; }
    .ticker-box { 
        display: inline-block; background-color: #f0f2f6; color: #5f6368; 
        font-weight: 600; font-size: 0.85rem; padding: 4px 10px; 
        border-radius: 6px; font-family: monospace; border: 1px solid #dadce0;
    }
    .just-link-btn { 
        display: inline-block; margin-top: 10px; padding: 8px 20px; 
        background-color: #ffffff; color: #1a73e8 !important; 
        text-decoration: none !important; border: 1px solid #1a73e8;
        border-radius: 20px; font-size: 0.75rem; font-weight: 600; 
        text-transform: uppercase; transition: all 0.3s ease;
    }
    .just-link-btn:hover { background-color: #1a73e8; color: white !important; }
    .euro-value { color: #2e7d32; font-weight: 700; font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SERVIZIO ---
def identify_isin(val1, val2=""):
    for v in [val1, val2]:
        s = str(v).strip().upper()
        if re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", s): return s
    return ""

@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency: return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose') or t.info.get('currentPrice')
        return float(rate) if rate else 1.0
    except: return 1.0

# --- LOGICA SALVATAGGIO LOCALE ---
def save_data_locally():
    if st.session_state.portfolio:
        df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
        df_save.to_csv(DB_FILE, index=False)
        return True
    return False

def load_data_locally():
    if os.path.exists(DB_FILE):
        try:
            df_load = pd.read_csv(DB_FILE).fillna("")
            new_port = {}
            for _, row in df_load.iterrows():
                t = str(row['Ticker']).strip().upper()
                new_port[t] = {
                    'Nome': row.get('Nome', t), 'ISIN': str(row.get('ISIN', '')).strip().upper(),
                    'Politica': str(row.get('Politica', 'Acc')), 'TER': str(row.get('TER', '')),
                    'Peso': float(row.get('Peso', 0)), 'Prezzo': float(row.get('Prezzo', 0)),
                    'Valuta': str(row.get('Valuta', 'EUR')), 'Cambio': float(row.get('Cambio', 1.0))
                }
            st.session_state.portfolio = new_port
            if 'Total_Budget' in df_load.columns:
                st.session_state.total_budget = float(df_load['Total_Budget'].iloc[0])
            return True
        except: return False
    return False

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    # Prova a caricare in automatico all'avvio
    load_data_locally()

if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.header("💾 Gestione File")

if st.sidebar.button("💾 SALVA PORTAFOGLIO"):
    if save_data_locally():
        st.sidebar.success(f"Portafoglio salvato in {DB_FILE}")
    else:
        st.sidebar.error("Nulla da salvare.")

# Caricamento manuale opzionale da altro file
uploaded_file = st.sidebar.file_uploader("Carica da un altro CSV", type="csv")
if uploaded_file:
    # ... (stessa logica di caricamento di prima)
    pass

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget))

st.sidebar.subheader("➕ Aggiungi Asset")
in_ticker = st.sidebar.text_input("Ticker Yahoo")
in_isin = st.sidebar.text_input("Codice ISIN")

if st.sidebar.button("Aggiungi ETF"):
    if in_ticker:
        t_up = in_ticker.upper().strip()
        try:
            with st.spinner("Dati in corso..."):
                y_info = yf.Ticker(t_up).info
                st.session_state.portfolio[t_up] = {
                    'Nome': y_info.get('longName', t_up), 
                    'ISIN': in_isin.upper().strip() if in_isin else y_info.get('isin', ''), 
                    'Politica': 'Dist' if y_info.get('dividendYield', 0) > 0 else 'Acc',
                    'TER': f"{y_info.get('annualReportExpenseRatio', 0.2)*100:.2f}%" if y_info.get('annualReportExpenseRatio') else "0.20%",
                    'Peso': 0.0, 'Prezzo': float(y_info.get('currentPrice') or y_info.get('previousClose') or 0),
                    'Valuta': y_info.get('currency', 'EUR'), 'Cambio': get_exchange_rate(y_info.get('currency', 'EUR'))
                }
                st.rerun()
        except: st.sidebar.error("Ticker non trovato.")

# --- MAIN DASHBOARD ---
st.title("💰 ETF PAC Planner")

if st.session_state.portfolio:
    cols = st.columns([3.8, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
    for col, lab in zip(cols, ["Dati ETF / JustETF", "Policy / TER", "Prezzo €", "Peso %", "Investimento", "Quote", ""]):
        col.write(f"**{lab}**")

    tot_w = 0
    tickers_for_graph = []
    
    for ticker, asset in st.session_state.portfolio.items():
        tickers_for_graph.append(ticker)
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3.8, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
        
        effective_isin = identify_isin(ticker, asset.get('ISIN', ''))
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome']}</div>", unsafe_allow_html=True)
            meta_str = f"{ticker}" + (f" | {effective_isin}" if effective_isin else "")
            st.markdown(f"<div class='ticker-box'>{meta_str}</div>", unsafe_allow_html=True)
            
            url_just = f"https://www.justetf.com/it/etf-profile.html?isin={effective_isin}" if effective_isin else f"https://www.justetf.com/it/find-etf.html?query={urllib.parse.quote(asset['Nome'])}"
            st.markdown(f"<a href='{url_just}' target='_blank' class='just-link-btn'>Vedi Scheda JustETF</a>", unsafe_allow_html=True)

        with c2:
            st.session_state.portfolio[ticker]['Politica'] = st.selectbox("Tipo", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"p_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['TER'] = st.text_input("TER", asset.get('TER', ''), key=f"t_{ticker}", label_visibility="collapsed")

        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        c3.write(f"**{p_eur:.2f} €**")
        w = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = w
        tot_w += w
        inv = (w / 100) * st.session_state.total_budget
        c5.markdown(f"<span class='euro-value'>{inv:,.2f} €</span>", unsafe_allow_html=True)
        q = inv / p_eur if p_eur > 0 else 0
        c6.write(f"**{q:.2f}**")
        if c7.button("🗑️", key=f"d_{ticker}"):
            del st.session_state.portfolio[ticker]; st.rerun()

    st.markdown("---")

    # --- PERFORMANCE E GRAFICO ---
    st.subheader("📈 Analisi Performance e Rendimento")
    
    if st.button("🚀 Aggiorna Analisi e Grafico"):
        with st.spinner("Analisi in corso..."):
            try:
                hist_data = yf.download(tickers_for_graph, period="1y")['Close']
                if len(tickers_for_graph) == 1: 
                    hist_data = hist_data.to_frame(); hist_data.columns = tickers_for_graph
                hist_data = hist_data.ffill().dropna()
                
                if not hist_data.empty:
                    norm = (hist_data / hist_data.iloc[0]) * 100
                    port_line = pd.Series(0.0, index=norm.index)
                    for t in tickers_for_graph:
                        port_line += norm[t] * (st.session_state.portfolio[t]['Peso'] / 100)
                    
                    # RENDIMENTI
                    ret_1y = port_line.iloc[-1] - 100
                    ret_6m = ((port_line.iloc[-1] / port_line.iloc[-len(port_line)//2]) - 1) * 100
                    
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Rendimento 1 Anno", f"{ret_1y:+.2f}%")
                    r2.metric("Rendimento 6 Mesi", f"{ret_6m:+.2f}%")
                    
                    perf_etf = ((hist_data.iloc[-1] / hist_data.iloc[0]) - 1) * 100
                    r3.metric("Miglior ETF (1A)", f"{perf_etf.idxmax()}", f"{perf_etf.max():+.2f}%")

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=port_line.index, y=port_line, name="IL TUO PAC", line=dict(color='#FF3B30', width=5)))
                    for t in tickers_for_graph:
                        fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=f"{t}", line=dict(width=1.2), opacity=0.3))
                    
                    fig.update_layout(template="plotly_white", hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True)
            except: st.error("Errore caricamento dati.")

    # Torta
    df_plot = pd.DataFrame([{'ETF': k, 'Peso': v['Peso']} for k,v in st.session_state.portfolio.items() if v['Peso']>0])
    if not df_plot.empty:
        st.plotly_chart(px.pie(df_plot, values='Peso', names='ETF', hole=0.4, title="Distribuzione Budget"), use_container_width=True)
else:
    st.info("👈 Carica un file o aggiungi un ETF per iniziare.")
