import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.express as px
import urllib.parse

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAC ETF Planner", layout="wide", page_icon="💰")

# CSS per pulizia visiva e link
st.markdown("""
    <style>
    .etf-name { color: #1E88E5; font-weight: bold; font-size: 1.05rem; margin-bottom: 0px; }
    .ticker-sub { color: #666; font-size: 0.85rem; margin-bottom: 5px; }
    .just-link-btn { 
        display: inline-block; 
        padding: 4px 12px; 
        background-color: #FB8C00; 
        color: white !important; 
        text-decoration: none; 
        border-radius: 4px; 
        font-size: 0.8rem; 
        font-weight: bold;
        margin-top: 5px;
        margin-bottom: 5px;
    }
    .just-link-btn:hover { background-color: #EF6C00; text-decoration: none; }
    .euro-value { color: #2e7d32; font-weight: bold; }
    /* Nasconde etichette e pulisce input */
    .stTextInput input { height: 30px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI ---
def get_justetf_metadata(isin):
    if not isin or isin == "N/A" or isin == "None": return None
    url = f"https://www.justetf.com/it/etf-profile.html?isin={isin}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            ter = ""
            for row in soup.find_all("div", class_="val"):
                if "%" in row.text:
                    ter = row.text.strip(); break
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

# --- STATO SESSIONE ---
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
            # Pulizia automatica dei "N/A" dal file caricato
            isin_raw = str(row.get('ISIN', ''))
            isin_clean = "" if isin_raw in ["N/A", "n/a", "None", "nan"] else isin_raw
            
            new_port[t] = {
                'Nome': row.get('Nome', t), 
                'ISIN': isin_clean,
                'Politica': str(row.get('Politica', 'Acc')), 
                'TER': str(row.get('TER', '0.20%')),
                'Peso': float(row.get('Peso', 0)), 
                'Prezzo': float(row.get('Prezzo', 0)),
                'Valuta': row.get('Valuta', 'EUR'), 
                'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_port
    except: st.sidebar.error("Errore lettura file.")

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
                isin_raw = y_info.get('isin', '')
                isin = "" if isin_raw in [None, "None", "N/A"] else isin_raw
                just_data = get_justetf_metadata(isin)
                st.session_state.portfolio[t_up] = {
                    'Nome': y_info.get('longName', t_up), 
                    'ISIN': isin,
                    'Politica': just_data['Politica'] if just_data else ('Dist' if y_info.get('dividendYield') else 'Acc'),
                    'TER': just_data['TER'] if just_data else '0.20%', 
                    'Peso': 0.0,
                    'Prezzo': float(y_info.get('currentPrice') or y_info.get('previousClose') or 0),
                    'Valuta': y_info.get('currency', 'EUR'), 
                    'Cambio': get_exchange_rate(y_info.get('currency', 'EUR'))
                }
                st.rerun()
        except: st.sidebar.error("Ticker non trovato.")

# --- MAIN ---
st.title("💰 ETF PAC Planner")

if st.session_state.portfolio:
    cols = st.columns([3.2, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
    header_labels = ["Dati ETF / JustETF", "Policy / TER", "Prezzo €", "Peso %", "Investimento", "Quote", ""]
    for col, lab in zip(cols, header_labels): col.write(f"**{lab}**")

    tot_w = 0
    for ticker, asset in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3.2, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
        
        # 1. NOME E LINK JUSTETF (Senza N/A)
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:55]}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='ticker-sub'>{ticker}</div>", unsafe_allow_html=True)
            
            # Gestione del link
            isin = asset.get('ISIN', '').strip()
            if isin and isin != "":
                # Se abbiamo l'ISIN, link diretto alla scheda
                just_url = f"https://www.justetf.com/it/etf-profile.html?isin={isin}"
                label = f"🔗 Scheda JustETF ({isin})"
            else:
                # Se manca l'ISIN, link alla ricerca per nome
                search_term = urllib.parse.quote(asset['Nome'])
                just_url = f"https://www.justetf.com/it/find-etf.html?query={search_term}"
                label = "🔍 Cerca su JustETF"
            
            st.markdown(f"<a href='{just_url}' target='_blank' class='just-link-btn'>{label}</a>", unsafe_allow_html=True)
            
            # Campo ISIN vuoto se non c'è, pronto per l'inserimento
            new_isin = st.text_input("Aggiorna ISIN", asset.get('ISIN', ''), key=f"isin_{ticker}", label_visibility="collapsed", placeholder="Incolla ISIN qui...")
            st.session_state.portfolio[ticker]['ISIN'] = new_isin

        # 2. POLICY / TER
        with c2:
            pol = st.selectbox("Pol", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"p_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['Politica'] = pol
            ter = st.text_input("TER", asset.get('TER', ''), key=f"t_{ticker}", label_visibility="collapsed", placeholder="es. 0.20%")
            st.session_state.portfolio[ticker]['TER'] = ter

        # 3. PREZZO
        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        c3.write(f"**{p_eur:.2f} €**")

        # 4. PESO
        w = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = w
        tot_w += w

        # 5. INVESTIMENTO
        inv = (w / 100) * st.session_state.total_budget
        c5.markdown(f"<span class='euro-value'>{inv:,.2f} €</span>", unsafe_allow_html=True)

        # 6. QUOTE
        q = inv / p_eur if p_eur > 0 else 0
        c6.write(f"**{q:.2f}**")

        # 7. DELETE
        if c7.button("🗑️", key=f"d_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    st.markdown("---")
    if tot_w != 100: st.warning(f"Allocazione budget attuale: {tot_w}%")
    else: st.success("✅ Budget 100% allocato correttamente.")
    
    # Grafico
    df_plot = pd.DataFrame([{'ETF': k, 'Peso': v['Peso']} for k,v in st.session_state.portfolio.items() if v['Peso']>0])
    if not df_plot.empty:
        st.plotly_chart(px.pie(df_plot, values='Peso', names='ETF', hole=0.4), use_container_width=True)
else:
    st.info("👈 Inizia aggiungendo un ticker Yahoo (es. SWDA.MI) o caricando un file CSV.")
