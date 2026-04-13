import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.express as px

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAC ETF Planner (JustETF Data)", layout="wide", page_icon="💰")

# --- FUNZIONI DI SCRAPING (Sperimentali) ---
def get_justetf_metadata(isin):
    """Tenta di recuperare TER e Politica da JustETF tramite ISIN"""
    if not isin or isin == "N/A":
        return None
    
    url = f"https://www.justetf.com/it/etf-profile.html?isin={isin}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ricerca TER
            ter = "N/A"
            if "Costi di gestione" in response.text:
                for row in soup.find_all("div", class_="val"):
                    if "%" in row.text:
                        ter = row.text.strip()
                        break
            
            # Ricerca Politica
            politica = "Acc"
            if "Distribuzione" in response.text:
                politica = "Dist"
            
            return {"TER": ter, "Politica": politica, "URL": url}
    except:
        pass
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
st.sidebar.header("💾 Salva/Carica")
uploaded_file = st.sidebar.file_uploader("Carica CSV", type="csv")
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
        st.sidebar.success("✅ Caricato!")
    except:
        st.sidebar.error("Errore nel file.")

# Export
if st.session_state.portfolio:
    df_save = pd.DataFrame([{'Ticker': k, **v} for k, v in st.session_state.portfolio.items()])
    st.sidebar.download_button("📥 Esporta CSV", df_save.to_csv(index=False).encode('utf-8'), "pac_etf.csv")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Impostazioni")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget))

st.sidebar.subheader("➕ Aggiungi ETF")
new_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI)")
if st.sidebar.button("Cerca e Analizza"):
    if new_ticker:
        t_up = new_ticker.upper().strip()
        try:
            with st.spinner("Recupero dati..."):
                y_obj = yf.Ticker(t_up)
                y_info = y_obj.info
                
                # 1. Prendi ISIN e Prezzo da Yahoo
                isin = y_info.get('isin', 'N/A')
                price = y_info.get('currentPrice') or y_info.get('previousClose') or 0.0
                curr = y_info.get('currency', 'EUR')
                
                # 2. Tenta Scraping da JustETF
                just_data = get_justetf_metadata(isin)
                
                st.session_state.portfolio[t_up] = {
                    'Nome': y_info.get('longName', t_up),
                    'ISIN': isin,
                    'Politica': just_data['Politica'] if just_data else 'Acc',
                    'TER': just_data['TER'] if just_data else '0.20%',
                    'Peso': 0.0,
                    'Prezzo': float(price),
                    'Valuta': curr,
                    'Cambio': get_exchange_rate(curr)
                }
                if just_data: st.toast(f"Dati JustETF recuperati per {isin}")
                st.rerun()
        except:
            st.sidebar.error("Errore nel recupero dati.")

# --- MAIN ---
st.title("💰 ETF PAC Planner")

if st.session_state.portfolio:
    # Header Tabella
    cols = st.columns([2.2, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
    for col, lab in zip(cols, ["ETF / ISIN", "Policy / TER", "Prezzo €", "Peso %", "Investimento", "Quote", ""]):
        col.write(f"**{lab}**")

    tot_w = 0
    for ticker, asset in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2.2, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
        
        with c1:
            st.markdown(f"**{ticker}**")
            isin_val = st.text_input("ISIN", asset['ISIN'], key=f"i_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['ISIN'] = isin_val
            if isin_val != "N/A":
                st.markdown(f"[🔗 JustETF](https://www.justetf.com/it/etf-profile.html?isin={isin_val})", unsafe_allow_html=True)

        with c2:
            pol = st.selectbox("Pol", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"p_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['Politica'] = pol
            ter = st.text_input("TER", asset['TER'], key=f"t_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['TER'] = ter

        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        c3.write(f"{p_eur:.2f} €")

        w = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = w
        tot_w += w

        inv = (w / 100) * st.session_state.total_budget
        c5.markdown(f"**{inv:,.2f} €**")

        q = inv / p_eur if p_eur > 0 else 0
        c6.write(f"{q:.2f}")

        if c7.button("🗑️", key=f"d_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    if tot_w != 100:
        st.warning(f"Allocazione budget: {tot_w}%")
    else:
        st.success("✅ Budget 100% allocato")

    st.plotly_chart(px.pie(pd.DataFrame([{'T':k, 'W':v['Peso']} for k,v in st.session_state.portfolio.items() if v['Peso']>0]), values='W', names='T', hole=0.4))
else:
    st.info("Aggiungi un ticker (es. SWDA.MI) per iniziare.")
