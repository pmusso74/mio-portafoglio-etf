import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import urllib.parse
import re
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner Pro", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv"

# CSS PER ESTETICA E VISIBILITÀ BOX
st.markdown("""
    <style>
    /* Stile per il titolo e i testi */
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 1.2rem; margin-bottom: 2px; }
    .isin-display { color: #d32f2f; font-weight: bold; font-family: monospace; font-size: 1rem; margin-bottom: 10px; }
    
    /* Box di ricerca ISIN nella sidebar */
    .search-container {
        background-color: #f0f7ff;
        padding: 20px;
        border-radius: 12px;
        border: 2px solid #1a73e8;
        margin-bottom: 20px;
    }
    
    /* Tasto JustETF elegante */
    .just-link-btn { 
        display: inline-block; margin-top: 10px; padding: 10px 24px; 
        background-color: #ffffff; color: #1a73e8 !important; 
        text-decoration: none !important; border: 1px solid #1a73e8;
        border-radius: 25px; font-size: 0.8rem; font-weight: 700; 
        text-transform: uppercase; transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .just-link-btn:hover { background-color: #1a73e8; color: white !important; }
    
    /* Metriche e Euro */
    .euro-value { color: #2e7d32; font-weight: 700; font-size: 1.15rem; }
    .pos-ret { color: #2e7d32; font-weight: 700; }
    .neg-ret { color: #d32f2f; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SERVIZIO ---
@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency: return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose') or t.info.get('currentPrice')
        return float(rate) if rate else 1.0
    except: return 1.0

def save_data_locally():
    if st.session_state.portfolio:
        df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
        df_save.to_csv(DB_FILE, index=False)
        return True
    return False

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE).fillna("")
        new_port = {}
        for _, row in df.iterrows():
            t = str(row['Ticker']).upper()
            new_port[t] = {
                'Nome': row.get('Nome', t), 'ISIN': str(row.get('ISIN', '')),
                'Politica': str(row.get('Politica', 'Acc')), 'TER': str(row.get('TER', '')),
                'Peso': float(row.get('Peso', 0)), 'Prezzo': float(row.get('Prezzo', 0)),
                'Valuta': str(row.get('Valuta', 'EUR')), 'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_port
        st.session_state.total_budget = float(df['Total_Budget'].iloc[0]) if 'Total_Budget' in df.columns else 1000.0

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    load_data()
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.title("📁 Gestione PAC")
if st.sidebar.button("💾 SALVA TUTTE LE MODIFICHE"):
    if save_data_locally(): st.sidebar.success("Portafoglio salvato su disco!")

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile Totale (€)", min_value=0.0, value=float(st.session_state.total_budget), step=50.0)

# BOX DI RICERCA ISIN PROMINENTE
st.sidebar.markdown("<div class='search-container'>", unsafe_allow_html=True)
st.sidebar.subheader("🔍 Aggiungi nuovo ETF")
target_isin = st.sidebar.text_input("Inserisci Codice ISIN", placeholder="es: IE00B4L5Y983").strip().upper()

if st.sidebar.button("CERCA E AGGIUNGI"):
    if target_isin:
        try:
            with st.spinner(f"Ricerca ISIN {target_isin} in corso..."):
                # Nota: yf.Ticker accetta anche l'ISIN direttamente per molti asset
                y_obj = yf.Ticker(target_isin)
                y_info = y_obj.info
                
                # Se yfinance non trova l'ISIN direttamente, cerchiamo il ticker corrispondente
                ticker_id = y_obj.ticker
                
                if 'longName' in y_info:
                    st.session_state.portfolio[ticker_id] = {
                        'Nome': y_info.get('longName', ticker_id),
                        'ISIN': target_isin,
                        'Politica': 'Dist' if y_info.get('dividendYield', 0) > 0 else 'Acc',
                        'TER': f"{y_info.get('annualReportExpenseRatio', 0.2)*100:.2f}%" if y_info.get('annualReportExpenseRatio') else "0.20%",
                        'Peso': 0.0,
                        'Prezzo': float(y_info.get('currentPrice') or y_info.get('previousClose') or 0),
                        'Valuta': y_info.get('currency', 'EUR'),
                        'Cambio': get_exchange_rate(y_info.get('currency', 'EUR'))
                    }
                    st.sidebar.success(f"Aggiunto: {y_info.get('longName')}")
                    st.rerun()
                else:
                    st.sidebar.error("ISIN non trovato. Prova a inserire il Ticker se lo conosci.")
                    # Fallback per ticker se l'ISIN fallisce
                    alt_ticker = st.sidebar.text_input("Inserimento manuale Ticker (se ISIN fallisce)", key="alt_t").upper()
                    if alt_ticker:
                        y_obj = yf.Ticker(alt_ticker)
                        # ... stessa logica di sopra ...
        except:
            st.sidebar.error("Errore nella ricerca. Verifica l'ISIN.")
st.sidebar.markdown("</div>", unsafe_allow_html=True)

# --- DASHBOARD PRINCIPALE ---
st.title("💰 Il mio Piano d'Accumulo")

if st.session_state.portfolio:
    cols = st.columns([4.0, 1.2, 1.0, 1.0, 1.5, 1.5, 0.5])
    for col, lab in zip(cols, ["Asset / Documentazione", "Dati Tecnici", "Prezzo €", "Peso %", "Investimento", "Quote", ""]):
        col.write(f"**{lab}**")

    tot_w = 0
    active_tickers = []
    for ticker, asset in st.session_state.portfolio.items():
        active_tickers.append(ticker)
        c1, c2, c3, c4, c5, c6, c7 = st.columns([4.0, 1.2, 1.0, 1.0, 1.5, 1.5, 0.5])
        
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='isin-display'>{asset['ISIN']}</div>", unsafe_allow_html=True)
            url_just = f"https://www.justetf.com/it/etf-profile.html?isin={asset['ISIN']}"
            st.markdown(f"<a href='{url_just}' target='_blank' class='just-link-btn'>Vai alla scheda JustETF</a>", unsafe_allow_html=True)

        with c2:
            st.session_state.portfolio[ticker]['Politica'] = st.selectbox("Tipo", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"p_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['TER'] = st.text_input("TER", asset.get('TER', ''), key=f"t_{ticker}", label_visibility="collapsed", placeholder="TER %")

        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        c3.write(f"**{p_eur:.2f} €**")
        w = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = w
        tot_w += w
        
        inv_mensile = (w / 100) * st.session_state.total_budget
        c5.markdown(f"<span class='euro-value'>{inv_mensile:,.2f} €</span>", unsafe_allow_html=True)
        
        quote = inv_mensile / p_eur if p_eur > 0 else 0
        c6.write(f"**{quote:.2f}**")
        
        if c7.button("🗑️", key=f"d_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    st.markdown("---")
    if tot_w != 100: st.warning(f"Budget allocato: {tot_w}% (deve essere 100%)")
    else: st.success("✅ Budget 100% allocato correttamente.")

    # --- ANALISI RENDIMENTI ---
    st.subheader("📈 Performance Storica del PAC")
    if st.button("🚀 GENERA ANALISI RENDIMENTI"):
        with st.spinner("Recupero dati storici in corso..."):
            try:
                data = yf.download(active_tickers, period="1y")['Close']
                if len(active_tickers) == 1: 
                    data = data.to_frame(); data.columns = active_tickers
                data = data.ffill().dropna()
                
                if not data.empty:
                    norm = (data / data.iloc[0]) * 100
                    port_line = pd.Series(0.0, index=norm.index)
                    for t in active_tickers:
                        port_line += norm[t] * (st.session_state.portfolio[t]['Peso'] / 100)
                    
                    # Calcolo Metriche
                    ret_1y = port_line.iloc[-1] - 100
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Rendimento PAC (1 Anno)", f"{ret_1y:+.2f}%")
                    
                    perf_etf = ((data.iloc[-1] / data.iloc[0]) - 1) * 100
                    best_t = perf_etf.idxmax()
                    r2.metric("Miglior ETF", st.session_state.portfolio[best_t]['Nome'][:20], f"{perf_etf.max():+.2f}%")

                    # Grafico
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=port_line.index, y=port_line, name="IL TUO PAC", line=dict(color='#FF3B30', width=4)))
                    for t in active_tickers:
                        fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=st.session_state.portfolio[t]['Nome'][:25], line=dict(width=1), opacity=0.3))
                    fig.update_layout(template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.1))
                    st.plotly_chart(fig, use_container_width=True)

                    # Rendimenti riga per riga
                    st.markdown("### 📋 Dettaglio Rendimenti Asset")
                    for t in active_tickers:
                        r_1y = ((data[t].iloc[-1] / data[t].iloc[0]) - 1) * 100
                        col_a, col_b, col_c = st.columns([4, 1, 2])
                        col_a.write(st.session_state.portfolio[t]['Nome'])
                        color_class = "pos-ret" if r_1y >= 0 else "neg-ret"
                        col_b.markdown(f"<span class='{color_class}'>{r_1y:+.2f}%</span>", unsafe_allow_html=True)
                        col_c.write(f"Inizio: {data[t].iloc[0]:.2f}€ → Fine: {data[t].iloc[-1]:.2f}€")
            except: st.error("Errore nel recupero dei dati storici.")

    # Grafico a torta
    df_plot = pd.DataFrame([{'ETF': v['Nome'], 'Peso': v['Peso']} for v in st.session_state.portfolio.values() if v['Peso'] > 0])
    if not df_plot.empty:
        st.plotly_chart(px.pie(df_plot, values='Peso', names='ETF', hole=0.4, title="Ripartizione del Portafoglio"), use_container_width=True)
else:
    st.info("👈 Inserisci un codice ISIN nella barra laterale blu per iniziare il tuo piano.")
