import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import urllib.parse
import re

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner", layout="wide", page_icon="💰")

# CSS per pulizia e stile
st.markdown("""
    <style>
    .etf-name { color: #1E88E5; font-weight: bold; font-size: 1.1rem; line-height: 1.2; }
    .etf-meta { color: #555; font-size: 0.9rem; margin-top: 2px; }
    .isin-code { color: #888; font-size: 0.85rem; font-family: monospace; font-weight: bold; }
    .just-link { 
        display: inline-block; margin-top: 6px; padding: 5px 12px; 
        background-color: #FB8C00; color: white !important; 
        text-decoration: none !important; border-radius: 4px; 
        font-size: 0.75rem; font-weight: bold; text-transform: uppercase;
    }
    .euro-value { color: #2e7d32; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---
def get_clean_isin(val):
    s = str(val).strip().upper()
    if s in ["N/A", "N/", "NONE", "NAN", "NULL", ""] or len(s) < 10: return ""
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

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state: st.session_state.portfolio = {}
if 'total_budget' not in st.session_state: st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.header("💾 Archivio")
uploaded_file = st.sidebar.file_uploader("Carica CSV", type="csv")
if uploaded_file:
    try:
        df_load = pd.read_csv(uploaded_file)
        new_port = {}
        for _, row in df_load.iterrows():
            t = str(row['Ticker'])
            new_port[t] = {
                'Nome': row.get('Nome', t), 'ISIN': get_clean_isin(row.get('ISIN', '')),
                'Politica': str(row.get('Politica', 'Acc')), 'TER': str(row.get('TER', '')).replace("nan", ""),
                'Peso': float(row.get('Peso', 0)), 'Prezzo': float(row.get('Prezzo', 0)),
                'Valuta': row.get('Valuta', 'EUR'), 'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_port
    except: st.sidebar.error("Errore caricamento CSV.")

if st.session_state.portfolio:
    df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
    st.sidebar.download_button("📥 Esporta CSV", df_save.to_csv(index=False).encode('utf-8'), "pac_etf.csv")

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget))

st.sidebar.subheader("➕ Aggiungi ETF")
new_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI)")
if st.sidebar.button("Aggiungi"):
    if new_ticker:
        t_up = new_ticker.upper().strip()
        try:
            with st.spinner("Recupero dati..."):
                y_info = yf.Ticker(t_up).info
                isin = get_clean_isin(y_info.get('isin', ''))
                st.session_state.portfolio[t_up] = {
                    'Nome': y_info.get('longName', t_up), 'ISIN': isin,
                    'Politica': 'Dist' if y_info.get('dividendYield', 0) > 0 else 'Acc',
                    'TER': f"{y_info.get('annualReportExpenseRatio', 0.2)*100:.2f}%" if y_info.get('annualReportExpenseRatio') else "0.20%",
                    'Peso': 0.0, 'Prezzo': float(y_info.get('currentPrice') or y_info.get('previousClose') or 0),
                    'Valuta': y_info.get('currency', 'EUR'), 'Cambio': get_exchange_rate(y_info.get('currency', 'EUR'))
                }
                st.rerun()
        except: st.sidebar.error("Ticker non trovato.")

# --- MAIN ---
st.title("💰 ETF PAC Planner")

if st.session_state.portfolio:
    cols = st.columns([3.5, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
    for col, lab in zip(cols, ["Dati ETF / JustETF", "Politica / TER", "Prezzo €", "Peso %", "Investimento", "Quote", ""]):
        col.write(f"**{lab}**")

    tot_w = 0
    tickers_list = []
    for ticker, asset in st.session_state.portfolio.items():
        tickers_list.append(ticker)
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3.5, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
        
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:60]}</div>", unsafe_allow_html=True)
            isin = asset.get('ISIN', '')
            meta_html = f"<div class='etf-meta'>{ticker}" + (f" | <span class='isin-code'>{isin}</span>" if isin else "") + "</div>"
            st.markdown(meta_html, unsafe_allow_html=True)
            
            # Link JustETF
            just_url = f"https://www.justetf.com/it/etf-profile.html?isin={isin}" if isin else f"https://www.justetf.com/it/find-etf.html?query={urllib.parse.quote(asset['Nome'])}"
            st.markdown(f"<a href='{just_url}' target='_blank' class='just-link'>🔗 {'Scheda' if isin else 'Cerca'} JustETF</a>", unsafe_allow_html=True)

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
    if tot_w != 100: st.warning(f"Allocazione attuale: {tot_w}% (deve essere 100%)")
    else: st.success("✅ Budget 100% allocato.")

    # --- SEZIONE GRAFICI ---
    t1, t2 = st.tabs(["📈 Performance Storica (1 Anno)", "📊 Distribuzione Budget"])
    
    with t1:
        if st.button("🚀 Carica/Aggiorna Grafico Storico"):
            with st.spinner("Elaborazione dati storici..."):
                try:
                    # Download dati 1 anno
                    data = yf.download(tickers_list, period="1y")['Close']
                    if len(tickers_list) == 1: 
                        data = data.to_frame()
                        data.columns = tickers_list
                    
                    data = data.ffill().dropna()
                    
                    if not data.empty:
                        # Normalizzazione Base 100
                        norm_data = (data / data.iloc[0]) * 100
                        
                        # Calcolo linea Portafoglio (PAC)
                        portfolio_line = pd.Series(0.0, index=norm_data.index)
                        for t in tickers_list:
                            weight = st.session_state.portfolio[t]['Peso'] / 100
                            portfolio_line += norm_data[t] * weight
                        
                        # Creazione Grafico con Plotly Graph Objects per maggiore controllo
                        fig = go.Figure()
                        
                        # Aggiunta linea Portafoglio (PAC)
                        fig.add_trace(go.Scatter(
                            x=portfolio_line.index, y=portfolio_line,
                            name="IL TUO PAC (Complessivo)",
                            line=dict(color='#FFD700', width=5), # Oro spesso
                        ))
                        
                        # Aggiunta linee singoli ETF
                        for t in tickers_list:
                            fig.add_trace(go.Scatter(
                                x=norm_data.index, y=norm_data[t],
                                name=f"{t}",
                                line=dict(width=1.5),
                                opacity=0.6
                            ))
                        
                        fig.update_layout(
                            title="Performance Relativa 1 Anno (Base 100)",
                            xaxis_title="Data",
                            yaxis_title="Valore Normalizzato",
                            hovermode="x unified",
                            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error("Dati non disponibili per questi ticker.")
                except Exception as e:
                    st.error(f"Errore nel calcolo del grafico: {e}")

    with t2:
        df_plot = pd.DataFrame([{'ETF': k, 'Peso': v['Peso']} for k,v in st.session_state.portfolio.items() if v['Peso']>0])
        if not df_plot.empty:
            st.plotly_chart(px.pie(df_plot, values='Peso', names='ETF', hole=0.4), use_container_width=True)
else:
    st.info("👈 Inizia aggiungendo un ticker Yahoo (es. SWDA.MI) dalla barra laterale.")
