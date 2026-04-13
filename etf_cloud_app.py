import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import urllib.parse
import re

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner", layout="wide", page_icon="💰")

# CSS PER ESTETICA ELEGANTE
st.markdown("""
    <style>
    /* Nome ETF */
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 1.2rem; line-height: 1.3; margin-bottom: 2px; }
    
    /* Box Ticker e ISIN */
    .ticker-box { 
        display: inline-block;
        background-color: #f0f2f6; 
        color: #5f6368; 
        font-weight: 600; 
        font-size: 0.85rem; 
        padding: 4px 10px; 
        border-radius: 6px; 
        font-family: 'Roboto Mono', monospace;
        border: 1px solid #dadce0;
    }

    /* TASTO JUSTETF ELEGANTE */
    .just-link-btn { 
        display: inline-block; 
        margin-top: 12px; 
        padding: 8px 20px; 
        background-color: #ffffff; 
        color: #1a73e8 !important; 
        text-decoration: none !important; 
        border: 1px solid #1a73e8;
        border-radius: 20px; 
        font-size: 0.75rem; 
        font-weight: 600; 
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 1px 2px rgba(60,64,67,0.3);
    }
    .just-link-btn:hover { 
        background-color: #1a73e8; 
        color: white !important; 
        box-shadow: 0 4px 6px rgba(60,64,67,0.15);
        transform: translateY(-1px);
    }

    /* Valori Euro */
    .euro-value { color: #2e7d32; font-weight: 700; font-size: 1.1rem; }
    
    /* Personalizzazione Input */
    .stTextInput input, .stSelectbox div div div { border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI ---
def identify_isin(val1, val2=""):
    for v in [val1, val2]:
        s = str(v).strip().upper()
        if re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", s):
            return s
    return ""

@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency: return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose') or t.info.get('currentPrice')
        return float(rate) if rate else 1.0
    except: return 1.0

# --- STATO SESSIONE ---
if 'portfolio' not in st.session_state: st.session_state.portfolio = {}
if 'total_budget' not in st.session_state: st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.header("💾 Archivio")
uploaded_file = st.sidebar.file_uploader("Carica CSV", type="csv")
if uploaded_file:
    try:
        df_load = pd.read_csv(uploaded_file).fillna("")
        new_port = {}
        for _, row in df_load.iterrows():
            t = str(row['Ticker']).strip().upper()
            new_port[t] = {
                'Nome': row.get('Nome', t), 'ISIN': str(row.get('ISIN', '')).strip().upper(),
                'Politica': str(row.get('Politica', 'Acc')), 'TER': str(row.get('TER', '')).replace("nan", ""),
                'Peso': float(row.get('Peso', 0)), 'Prezzo': float(row.get('Prezzo', 0)),
                'Valuta': str(row.get('Valuta', 'EUR')), 'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_port
    except: st.sidebar.error("Errore file.")

if st.session_state.portfolio:
    df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
    st.sidebar.download_button("📥 Esporta CSV", df_save.to_csv(index=False).encode('utf-8'), "mio_pac.csv")

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget))

st.sidebar.subheader("➕ Aggiungi Asset")
in_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI)")
in_isin = st.sidebar.text_input("Codice ISIN")

if st.sidebar.button("Aggiungi ETF"):
    if in_ticker:
        t_up = in_ticker.upper().strip()
        isin_up = in_isin.upper().strip()
        try:
            with st.spinner("Recupero dati..."):
                y_info = yf.Ticker(t_up).info
                st.session_state.portfolio[t_up] = {
                    'Nome': y_info.get('longName', t_up), 
                    'ISIN': isin_up if isin_up else y_info.get('isin', ''), 
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
            
            # Box Ticker/ISIN
            if ticker == effective_isin:
                st.markdown(f"<div class='ticker-box'>{effective_isin}</div>", unsafe_allow_html=True)
            else:
                meta_str = f"{ticker}" + (f" | {effective_isin}" if effective_isin else "")
                st.markdown(f"<div class='ticker-box'>{meta_str}</div>", unsafe_allow_html=True)
            
            # Tasto JustETF Elegante
            if effective_isin:
                url_just = f"https://www.justetf.com/it/etf-profile.html?isin={effective_isin}"
                label_just = "Vedi Scheda JustETF"
            else:
                query_name = urllib.parse.quote(asset['Nome'])
                url_just = f"https://www.justetf.com/it/find-etf.html?query={query_name}"
                label_just = "🔍 Cerca su JustETF"
            
            st.markdown(f"<a href='{url_just}' target='_blank' class='just-link-btn'>{label_just}</a>", unsafe_allow_html=True)

        with c2:
            st.session_state.portfolio[ticker]['Politica'] = st.selectbox("Tipo", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"p_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['TER'] = st.text_input("TER", asset.get('TER', ''), key=f"t_{ticker}", label_visibility="collapsed", placeholder="TER %")

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
    if tot_w != 100: st.warning(f"Allocazione budget: {tot_w}% (deve essere 100%)")
    else: st.success("✅ Budget 100% allocato correttamente.")

    # --- GRAFICO PERFORMANCE ---
    st.subheader("📈 Analisi Performance Storica")
    if st.button("🚀 Genera Grafico"):
        with st.spinner("Caricamento dati..."):
            try:
                hist_data = yf.download(tickers_for_graph, period="1y")['Close']
                if len(tickers_for_graph) == 1: 
                    hist_data = hist_data.to_frame()
                    hist_data.columns = tickers_for_graph
                hist_data = hist_data.ffill().dropna()
                
                if not hist_data.empty:
                    norm = (hist_data / hist_data.iloc[0]) * 100
                    port_line = pd.Series(0.0, index=norm.index)
                    for t in tickers_for_graph:
                        port_line += norm[t] * (st.session_state.portfolio[t]['Peso'] / 100)
                    
                    fig = go.Figure()
                    # LINEA PAC ROSSA
                    fig.add_trace(go.Scatter(
                        x=port_line.index, y=port_line, 
                        name="IL TUO PAC", 
                        line=dict(color='#FF3B30', width=4) # Rosso Apple Style
                    ))
                    # Linee sottili per gli altri
                    for t in tickers_for_graph:
                        fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=f"{t}", line=dict(width=1.2), opacity=0.4))
                    
                    fig.update_layout(template="plotly_white", hovermode="x unified", yaxis_title="Valore Normalizzato (Base 100)")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error("Dati non trovati.")
            except Exception as e:
                st.error(f"Errore: {e}")
else:
    st.info("👈 Inserisci Ticker e ISIN nella barra laterale per iniziare.")
