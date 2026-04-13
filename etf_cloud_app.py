import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import urllib.parse

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner", layout="wide", page_icon="💰")

# CSS per pulizia e stile
st.markdown("""
    <style>
    .etf-name { color: #1E88E5; font-weight: bold; font-size: 1.1rem; line-height: 1.2; }
    .etf-meta { color: #555; font-size: 0.95rem; margin-top: 3px; font-weight: 500; }
    .isin-code { color: #D32F2F; font-family: monospace; font-weight: bold; }
    .just-link { 
        display: inline-block; margin-top: 8px; padding: 6px 14px; 
        background-color: #FB8C00; color: white !important; 
        text-decoration: none !important; border-radius: 4px; 
        font-size: 0.75rem; font-weight: bold; text-transform: uppercase;
    }
    .just-link:hover { background-color: #EF6C00; }
    .euro-value { color: #2e7d32; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI PULIZIA ---
def clean_val(val):
    """Rimuove nan, N/A e trasforma in stringa pulita"""
    if pd.isna(val) or str(val).lower() in ["nan", "n/a", "none", "null"]:
        return ""
    return str(val).strip()

@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency: return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose') or t.info.get('currentPrice')
        return float(rate) if rate else 1.0
    except: return 1.0

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state: st.session_state.portfolio = {}
if 'total_budget' not in st.session_state: st.session_state.total_budget = 1000.0

# --- SIDEBAR: CARICAMENTO ---
st.sidebar.header("💾 Archivio")
uploaded_file = st.sidebar.file_uploader("Carica CSV", type="csv")
if uploaded_file:
    try:
        df_load = pd.read_csv(uploaded_file).fillna("") # Sostituisce nan con stringa vuota
        new_port = {}
        for _, row in df_load.iterrows():
            t = clean_val(row['Ticker'])
            if not t: continue
            new_port[t] = {
                'Nome': clean_val(row.get('Nome', t)), 
                'ISIN': clean_val(row.get('ISIN', '')),
                'Politica': clean_val(row.get('Politica', 'Acc')), 
                'TER': clean_val(row.get('TER', '0.20%')),
                'Peso': float(row.get('Peso', 0)), 
                'Prezzo': float(row.get('Prezzo', 0)),
                'Valuta': clean_val(row.get('Valuta', 'EUR')), 
                'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_port
    except: st.sidebar.error("Errore nel formato del CSV.")

if st.session_state.portfolio:
    df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
    st.sidebar.download_button("📥 Esporta CSV", df_save.to_csv(index=False).encode('utf-8'), "pac_etf.csv")

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget))

st.sidebar.subheader("➕ Aggiungi ETF")
input_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI)")
input_isin = st.sidebar.text_input("Codice ISIN (es: IE00B4L5Y983)")

if st.sidebar.button("Aggiungi Asset"):
    if input_ticker:
        t_up = input_ticker.upper().strip()
        isin_up = input_isin.upper().strip()
        try:
            with st.spinner("Connessione a Yahoo Finance..."):
                y_info = yf.Ticker(t_up).info
                st.session_state.portfolio[t_up] = {
                    'Nome': y_info.get('longName', t_up), 
                    'ISIN': isin_up, 
                    'Politica': 'Dist' if y_info.get('dividendYield', 0) > 0 else 'Acc',
                    'TER': f"{y_info.get('annualReportExpenseRatio', 0.2)*100:.2f}%" if y_info.get('annualReportExpenseRatio') else "0.20%",
                    'Peso': 0.0, 
                    'Prezzo': float(y_info.get('currentPrice') or y_info.get('previousClose') or 0),
                    'Valuta': y_info.get('currency', 'EUR'), 
                    'Cambio': get_exchange_rate(y_info.get('currency', 'EUR'))
                }
                st.rerun()
        except: st.sidebar.error("Ticker non trovato.")

# --- MAIN DASHBOARD ---
st.title("💰 ETF PAC Planner")

if st.session_state.portfolio:
    cols = st.columns([3.5, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
    header_labels = ["Dati ETF / JustETF", "Politica / TER", "Prezzo €", "Peso %", "Investimento", "Quote", ""]
    for col, lab in zip(cols, header_labels): col.write(f"**{lab}**")

    tot_w = 0
    tickers_list = []
    for ticker, asset in st.session_state.portfolio.items():
        tickers_list.append(ticker)
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3.5, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
        
        # 1. NOME, TICKER, ISIN (PULIZIA TOTALE)
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:60]}</div>", unsafe_allow_html=True)
            
            isin = clean_val(asset.get('ISIN', ''))
            
            # Costruiamo la riga Ticker | ISIN solo se l'ISIN esiste
            meta_str = f"{ticker}"
            if isin != "":
                meta_str += f" | <span class='isin-code'>{isin}</span>"
            
            st.markdown(f"<div class='etf-meta'>{meta_str}</div>", unsafe_allow_html=True)
            
            # LINK JUSTETF (Senza nan o N/A)
            if isin != "":
                url = f"https://www.justetf.com/it/etf-profile.html?isin={isin}"
                label = f"Scheda JustETF ({isin})"
            else:
                # Se l'ISIN manca, facciamo ricerca per Nome
                q = urllib.parse.quote(asset['Nome'])
                url = f"https://www.justetf.com/it/find-etf.html?query={q}"
                label = "Cerca su JustETF (ISIN assente)"
            
            st.markdown(f"<a href='{url}' target='_blank' class='just-link'>🔗 {label}</a>", unsafe_allow_html=True)

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

    # --- GRAFICO STORICO ---
    st.subheader("📈 Analisi Performance Storica")
    if st.button("🚀 Genera / Aggiorna Grafico"):
        with st.spinner("Scaricamento dati storici (1 anno)..."):
            try:
                data = yf.download(tickers_list, period="1y")['Close']
                if len(tickers_list) == 1: 
                    data = data.to_frame()
                    data.columns = tickers_list
                data = data.ffill().dropna()
                
                if not data.empty:
                    # Normalizzazione a base 100
                    norm = (data / data.iloc[0]) * 100
                    
                    # Calcolo linea del Portafoglio (PAC)
                    port_line = pd.Series(0.0, index=norm.index)
                    for t in tickers_list:
                        port_line += norm[t] * (st.session_state.portfolio[t]['Peso'] / 100)
                    
                    fig = go.Figure()
                    # Linea PAC (Oro spessa)
                    fig.add_trace(go.Scatter(x=port_line.index, y=port_line, name="IL TUO PAC", line=dict(color='#FFD700', width=5)))
                    
                    # Linee singoli ETF
                    for t in tickers_list:
                        fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=f"{t}", line=dict(width=1.5), opacity=0.5))
                    
                    fig.update_layout(title="Andamento Storico Normalizzato (Base 100)", hovermode="x unified", template="plotly_white", yaxis_title="Valore Relativo")
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Errore caricamento grafico: {e}")

    # Grafico a torta distribuzione
    df_plot = pd.DataFrame([{'ETF': k, 'Peso': v['Peso']} for k,v in st.session_state.portfolio.items() if v['Peso']>0])
    if not df_plot.empty:
        st.plotly_chart(px.pie(df_plot, values='Peso', names='ETF', hole=0.4, title="Distribuzione Budget Mensile"), use_container_width=True)
else:
    st.info("👈 Inserisci Ticker e ISIN nella barra laterale per iniziare.")
