import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.express as px

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAC ETF Planner (Full Info)", layout="wide", page_icon="💰")

# CSS per rifiniture estetiche
st.markdown("""
    <style>
    .etf-name { color: #1E88E5; font-weight: bold; font-size: 1.05rem; margin-bottom: -10px; }
    .ticker-sub { color: #666; font-size: 0.85rem; margin-top: 0px; margin-bottom: 5px; }
    .just-link { font-size: 0.8rem; text-decoration: none; color: #FB8C00; font-weight: bold; }
    .euro-value { color: #2e7d32; font-weight: bold; font-size: 1.1rem; }
    .stTextInput input { height: 28px; font-size: 0.85rem; }
    .stSelectbox div div div { height: 28px; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---
def get_justetf_metadata(isin):
    """Tenta di recuperare TER e Politica da JustETF tramite ISIN"""
    if not isin or isin == "N/A": return None
    url = f"https://www.justetf.com/it/etf-profile.html?isin={isin}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            ter = "N/A"
            for row in soup.find_all("div", class_="val"):
                if "%" in row.text:
                    ter = row.text.strip()
                    break
            politica = "Dist" if "Distribuzione" in response.text else "Acc"
            return {"TER": ter, "Politica": politica}
    except: pass
    return None

@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency: return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose') or t.info.get('currentPrice')
        return float(rate) if rate else 1.0
    except: return 1.0

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- SIDEBAR: GESTIONE ---
st.sidebar.header("💾 Gestione File")
uploaded_file = st.sidebar.file_uploader("Carica Portafoglio CSV", type="csv")
if uploaded_file is not None:
    try:
        df_load = pd.read_csv(uploaded_file)
        new_port = {}
        for _, row in df_load.iterrows():
            t = str(row['Ticker'])
            new_port[t] = {
                'Nome': row.get('Nome', t),
                'ISIN': str(row.get('ISIN', 'N/A')),
                'Politica': str(row.get('Politica', 'Acc')),
                'TER': str(row.get('TER', '0.00%')),
                'Peso': float(row.get('Peso', 0)),
                'Prezzo': float(row.get('Prezzo', 0)),
                'Valuta': row.get('Valuta', 'EUR'),
                'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_port
        if 'Total_Budget' in df_load.columns:
            st.session_state.total_budget = float(df_load['Total_Budget'].iloc[0])
        st.sidebar.success("✅ Caricato!")
    except: st.sidebar.error("Errore nel caricamento del file.")

if st.session_state.portfolio:
    df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
    st.sidebar.download_button("📥 Esporta Portafoglio", df_save.to_csv(index=False).encode('utf-8'), "mio_pac_etf.csv")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Impostazioni PAC")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget))

st.sidebar.subheader("➕ Aggiungi ETF")
new_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI)")
if st.sidebar.button("Aggiungi Asset"):
    if new_ticker:
        t_up = new_ticker.upper().strip()
        try:
            with st.spinner("Recupero dati da Yahoo e JustETF..."):
                y_info = yf.Ticker(t_up).info
                isin = y_info.get('isin', 'N/A')
                price = y_info.get('currentPrice') or y_info.get('previousClose') or 0.0
                curr = y_info.get('currency', 'EUR')
                
                just_data = get_justetf_metadata(isin)
                
                st.session_state.portfolio[t_up] = {
                    'Nome': y_info.get('longName', t_up),
                    'ISIN': isin,
                    'Politica': just_data['Politica'] if just_data else ('Dist' if y_info.get('dividendYield') else 'Acc'),
                    'TER': just_data['TER'] if just_data else '0.20%',
                    'Peso': 0.0,
                    'Prezzo': float(price),
                    'Valuta': curr,
                    'Cambio': get_exchange_rate(curr)
                }
                st.rerun()
        except: st.sidebar.error("Ticker non trovato.")

# --- AREA PRINCIPALE ---
st.title("💰 ETF PAC Planner")
st.markdown(f"Budget mensile totale da allocare: <span class='euro-value'>{st.session_state.total_budget:,.2f} €</span>", unsafe_allow_html=True)

if st.session_state.portfolio:
    # Header Tabella
    cols = st.columns([2.8, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
    for col, lab in zip(cols, ["Dati ETF / ISIN", "Policy / TER", "Prezzo €", "Peso %", "Investimento", "Quote", ""]):
        col.write(f"**{lab}**")

    tot_w = 0
    for ticker, asset in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2.8, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
        
        # 1. NOME, TICKER, ISIN
        with c1:
            st.markdown(f"<div class='etf-name'>{asset.get('Nome', ticker)[:45]}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='ticker-sub'>{ticker}</div>", unsafe_allow_html=True)
            isin_val = st.text_input("ISIN", asset.get('ISIN', 'N/A'), key=f"i_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['ISIN'] = isin_val
            if isin_val != "N/A":
                st.markdown(f"<a class='just-link' href='https://www.justetf.com/it/etf-profile.html?isin={isin_val}' target='_blank'>🔗 APRI SU JUSTETF</a>", unsafe_allow_html=True)

        # 2. POLICY e TER
        with c2:
            pol = st.selectbox("Pol", ["Acc", "Dist"], index=0 if asset.get('Politica')=="Acc" else 1, key=f"p_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['Politica'] = pol
            ter = st.text_input("TER", asset.get('TER', '0.20%'), key=f"t_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['TER'] = ter

        # 3. PREZZO EUR
        p_eur = asset.get('Prezzo', 0) * asset.get('Cambio', 1.0)
        c3.write(f"**{p_eur:.2f} €**")

        # 4. PESO %
        with c4:
            w = st.number_input("%", 0, 100, int(asset.get('Peso', 0)), key=f"w_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['Peso'] = w
            tot_w += w

        # 5. INVESTIMENTO
        inv = (w / 100) * st.session_state.total_budget
        c5.markdown(f"<span class='euro-value'>{inv:,.2f} €</span>", unsafe_allow_html=True)

        # 6. QUOTE
        q = inv / p_eur if p_eur > 0 else 0
        c6.markdown(f"<span style='font-weight:500;'>{q:.2f}</span>", unsafe_allow_html=True)

        # 7. ELIMINA
        if c7.button("🗑️", key=f"d_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    # Footer Validazione
    st.markdown("---")
    if tot_w != 100:
        st.warning(f"⚠️ Allocazione attuale: **{tot_w}%** del budget. (Manca il {100-tot_w}%)")
    else:
        st.success("✅ Budget 100% allocato correttamente.")

    # Grafico
    df_plot = pd.DataFrame([{'ETF': k, 'Peso': v['Peso']} for k,v in st.session_state.portfolio.items() if v['Peso']>0])
    if not df_plot.empty:
        st.plotly_chart(px.pie(df_plot, values='Peso', names='ETF', hole=0.4), use_container_width=True)
else:
    st.info("👈 Inizia aggiungendo un ticker dalla barra laterale (es. SWDA.MI, CSSPX.MI, EIMI.MI)")
