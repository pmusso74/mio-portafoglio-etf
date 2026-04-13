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

# --- CSS PER ESTETICA AVANZATA ---
st.markdown("""
    <style>
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 1.1rem; margin-bottom: 2px; }
    .isin-display { color: #d32f2f; font-weight: bold; font-family: monospace; font-size: 0.9rem; margin-bottom: 10px; }
    .search-container { background-color: #f0f7ff; padding: 15px; border-radius: 10px; border: 1px solid #1a73e8; margin-bottom: 20px; }
    .just-link-btn { 
        display: inline-block; margin-top: 8px; padding: 6px 18px; 
        background-color: #ffffff; color: #1a73e8 !important; 
        text-decoration: none !important; border: 1px solid #1a73e8;
        border-radius: 20px; font-size: 0.75rem; font-weight: 700; 
        text-transform: uppercase; transition: all 0.3s ease;
    }
    .just-link-btn:hover { background-color: #1a73e8; color: white !important; }
    .small-metric-label { font-size: 0.9rem; color: #5f6368; margin-bottom: 2px; font-weight: 500; }
    .small-metric-value { font-size: 1.25rem; font-weight: 800; color: #1a1c1e; }
    .best-asset-value { font-size: 1.1rem; font-weight: 800; color: #1a73e8; }
    .best-asset-pct { font-size: 1.05rem; font-weight: 700; color: #2e7d32; }
    .euro-value { color: #2e7d32; font-weight: 700; font-size: 1.05rem; }
    .weekly-value { color: #1a73e8; font-weight: 700; font-size: 1.05rem; }
    .pos-ret { color: #2e7d32; font-weight: 700; }
    .neg-ret { color: #d32f2f; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---
@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency: return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose') or t.info.get('currentPrice')
        return float(rate) if rate else 1.0
    except: return 1.0

@st.cache_data(ttl=300)
def fetch_historical_data(tickers):
    if not tickers: return pd.DataFrame()
    data = yf.download(list(tickers), period="1y", progress=False)['Close']
    if len(tickers) == 1:
        data = data.to_frame()
        data.columns = list(tickers)
    return data.ffill().dropna()

def load_from_df(df):
    df = df.fillna("")
    new_port = {}
    for _, row in df.iterrows():
        t = str(row['Ticker']).upper()
        new_port[t] = {
            'Nome': row.get('Nome', t), 
            'ISIN': str(row.get('ISIN', '')),
            'Politica': str(row.get('Politica', 'Acc')), 
            'TER': str(row.get('TER', '')),
            'Peso': float(row.get('Peso', 0)), 
            'Prezzo': float(row.get('Prezzo', 0)),
            'Valuta': str(row.get('Valuta', 'EUR')), 
            'Cambio': float(row.get('Cambio', 1.0))
        }
    st.session_state.portfolio = new_port
    if 'Total_Budget' in df.columns:
        st.session_state.total_budget = float(df['Total_Budget'].iloc[0])

def save_data_locally():
    if st.session_state.portfolio:
        df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
        df_save.to_csv(DB_FILE, index=False)
        return True
    return False

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    if os.path.exists(DB_FILE):
        load_from_df(pd.read_csv(DB_FILE))

if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.title("📁 Gestione Portafoglio")

if st.sidebar.button("💾 SALVA PORTAFOGLIO"):
    if save_data_locally(): st.sidebar.success("Salvato correttamente!")

st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader("📥 Carica CSV esterno", type="csv")
if uploaded_file is not None:
    try:
        load_from_df(pd.read_csv(uploaded_file))
        st.sidebar.success("File caricato!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Errore: {e}")

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget), step=50.0)

# Calcolo settimanale totale
weekly_total = st.session_state.total_budget / 4.33
st.sidebar.markdown(f"**Budget Settimanale: {weekly_total:,.2f} €**")

st.sidebar.markdown("<div class='search-container'>", unsafe_allow_html=True)
st.sidebar.subheader("🔍 Aggiungi ETF")
target_isin = st.sidebar.text_input("Inserisci Codice ISIN", placeholder="es: IE00B4L5Y983").strip().upper()

if st.sidebar.button("CERCA E AGGIUNGI"):
    if target_isin:
        try:
            with st.spinner("Analisi..."):
                y_obj = yf.Ticker(target_isin)
                y_info = y_obj.info
                ticker_id = y_obj.ticker
                if 'longName' in y_info:
                    st.session_state.portfolio[ticker_id] = {
                        'Nome': y_info.get('longName', ticker_id),
                        'ISIN': target_isin,
                        'Politica': 'Dist' if y_info.get('dividendYield', 0) > 0 else 'Acc',
                        'TER': f"{y_info.get('annualReportExpenseRatio', 0.002)*100:.2f}%" if y_info.get('annualReportExpenseRatio') else "0.20%",
                        'Peso': 0.0,
                        'Prezzo': float(y_info.get('currentPrice') or y_info.get('previousClose') or 0),
                        'Valuta': y_info.get('currency', 'EUR'),
                        'Cambio': get_exchange_rate(y_info.get('currency', 'EUR'))
                    }
                    st.rerun()
        except: st.sidebar.error("ISIN non trovato.")
st.sidebar.markdown("</div>", unsafe_allow_html=True)

# --- DASHBOARD PRINCIPALE ---
st.title("💰 Il mio Piano d'Accumulo")

if st.session_state.portfolio:
    # Colonne ricalibrate per ospitare il dato settimanale
    cols = st.columns([2.8, 1.0, 0.8, 0.7, 1.1, 1.1, 1.1, 0.4])
    header_labels = ["Asset / JustETF", "Dati", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Quote Sett.", ""]
    for col, lab in zip(cols, header_labels): col.write(f"**{lab}**")

    tot_w = 0
    all_tickers = list(st.session_state.portfolio.keys())
    
    for ticker, asset in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.8, 1.0, 0.8, 0.7, 1.1, 1.1, 1.1, 0.4])
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:50]}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='isin-display'>{asset['ISIN']}</div>", unsafe_allow_html=True)
            url_just = f"https://www.justetf.com/it/etf-profile.html?isin={asset['ISIN']}"
            st.markdown(f"<a href='{url_just}' target='_blank' class='just-link-btn'>JustETF</a>", unsafe_allow_html=True)

        with c2:
            st.session_state.portfolio[ticker]['Politica'] = st.selectbox("Tipo", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"p_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['TER'] = st.text_input("TER", asset.get('TER', ''), key=f"t_{ticker}", label_visibility="collapsed", placeholder="%")

        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        c3.write(f"**{p_eur:.2f}**")
        
        w = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = w
        tot_w += w
        
        # Calcoli Money
        inv_m = (w / 100) * st.session_state.total_budget
        inv_w = inv_m / 4.33
        
        c5.markdown(f"<span class='euro-value'>{inv_m:,.2f}</span>", unsafe_allow_html=True)
        c6.markdown(f"<span class='weekly-value'>{inv_w:,.2f}</span>", unsafe_allow_html=True)
        
        # Quote settimanali
        q_w = inv_w / p_eur if p_eur > 0 else 0
        c7.write(f"**{q_w:.2f}**")
        
        if c8.button("🗑️", key=f"d_{ticker}"):
            del st.session_state.portfolio[ticker]; st.rerun()

    st.markdown("---")

    # --- ANALISI AUTOMATICA ---
    st.subheader("📈 Performance Storica Aggiornata")
    tickers_attivi = [t for t in all_tickers if st.session_state.portfolio[t]['Peso'] > 0]

    try:
        data = fetch_historical_data(tuple(all_tickers)) 
        if not data.empty and tickers_attivi:
            tot_w_inserito = sum(st.session_state.portfolio[t]['Peso'] for t in tickers_attivi)
            norm = (data / data.iloc[0]) * 100
            port_line = pd.Series(0.0, index=norm.index)
            for t in tickers_attivi:
                w_relativo = st.session_state.portfolio[t]['Peso'] / tot_w_inserito
                port_line += norm[t] * w_relativo
            
            ret_1y = port_line.iloc[-1] - 100
            ret_6m = ((port_line.iloc[-1] / port_line.iloc[-len(port_line)//2]) - 1) * 100
            perf_attivi = ((data[tickers_attivi].iloc[-1] / data[tickers_attivi].iloc[0]) - 1) * 100
            best_t = perf_attivi.idxmax()

            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(f"<div class='small-metric-label'>Rendimento PAC (1 Anno)</div><div class='small-metric-value'>{ret_1y:+.2f}%</div>", unsafe_allow_html=True)
            with m2:
                st.markdown(f"<div class='small-metric-label'>Rendimento PAC (6 Mesi)</div><div class='small-metric-value'>{ret_6m:+.2f}%</div>", unsafe_allow_html=True)
            with m3:
                st.markdown(f"<div class='small-metric-label'>🏆 Miglior Asset Attivo (1 Anno)</div><div class='best-asset-value'>{st.session_state.portfolio[best_t]['Nome'][:40]}</div><div class='best-asset-pct'>{perf_attivi.max():+.2f}%</div>", unsafe_allow_html=True)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=port_line.index, y=port_line, name="IL TUO PAC", line=dict(color='#FF3B30', width=5)))
            for t in tickers_attivi:
                fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=st.session_state.portfolio[t]['Nome'][:25], line=dict(width=2), opacity=0.8))
            fig.update_layout(template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.15))
            st.plotly_chart(fig, use_container_width=True)

            # Dettaglio Rendimenti riga per riga
            st.markdown("### 📋 Dettaglio Rendimenti Asset Attivi")
            for t in tickers_attivi:
                r_1y = ((data[t].iloc[-1] / data[t].iloc[0]) - 1) * 100
                r_6m = ((data[t].iloc[-1] / data[t].iloc[-len(data)//2]) - 1) * 100
                ca, cb, cc, cd = st.columns([3, 1, 1, 2])
                ca.write(f"**{st.session_state.portfolio[t]['Nome']}**")
                cb.markdown(f"<span class='{'pos-ret' if r_1y>=0 else 'neg-ret'}'>1A: {r_1y:+.2f}%</span>", unsafe_allow_html=True)
                cc.markdown(f"<span class='{'pos-ret' if r_6m>=0 else 'neg-ret'}'>6M: {r_6m:+.2f}%</span>", unsafe_allow_html=True)
                cd.write(f"{data[t].iloc[0]:.2f}€ → {data[t].iloc[-1]:.2f}€")
        elif not tickers_attivi:
            st.warning("Imposta una percentuale di peso (%) su almeno un ETF per attivare l'analisi.")
    except Exception as e:
        st.error(f"Errore caricamento analisi: {e}")

    # Torta
    df_plot = pd.DataFrame([{'ETF': v['Nome'], 'Peso': v['Peso']} for v in st.session_state.portfolio.values() if v['Peso'] > 0])
    if not df_plot.empty:
        st.plotly_chart(px.pie(df_plot, values='Peso', names='ETF', hole=0.4, title="Ripartizione Effettiva Budget"), use_container_width=True)
else:
    st.info("👈 Inserisci un ISIN nella barra laterale per iniziare.")
