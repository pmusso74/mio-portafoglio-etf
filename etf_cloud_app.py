import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# --- CONFIGURAZIONE DATABASE ---
# Inserisci qui i tuoi dati Supabase o usa i "secrets" di Streamlit
URL = st.sidebar.text_input("Supabase URL", type="password")
KEY = st.sidebar.text_input("Supabase Key", type="password")

def get_supabase():
    if URL and KEY:
        return create_client(URL, KEY)
    return None

# --- FUNZIONI DI SALVATAGGIO ---
def save_to_cloud(portfolio_id, portfolio_dict, monthly_inv):
    supabase = get_supabase()
    if supabase:
        data = {
            "id": portfolio_id,
            "data": portfolio_dict,
            "monthly_investment": monthly_inv
        }
        supabase.table("portfolios").upsert(data).execute()
        st.sidebar.success("✅ Salvato nel Cloud!")
    else:
        st.sidebar.error("Configura URL e Key di Supabase")

def load_from_cloud(portfolio_id):
    supabase = get_supabase()
    if supabase:
        response = supabase.table("portfolios").select("*").eq("id", portfolio_id).execute()
        if response.data:
            return response.data[0]
    return None

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Cloud ETF Monitor", layout="wide")
st.title("🌐 Cloud ETF Portfolio Manager")

# Sidebar per Accesso
st.sidebar.header("🔐 Accesso Portafoglio")
portfolio_id = st.sidebar.text_input("ID Portafoglio (es: mio_portafoglio_2024)", "default_user")

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    st.session_state.monthly_investment = 1000.0

# Caricamento iniziale
if st.sidebar.button("Carica dal Cloud"):
    cloud_data = load_from_cloud(portfolio_id)
    if cloud_data:
        st.session_state.portfolio = cloud_data['data']
        st.session_state.monthly_investment = cloud_data['monthly_investment']
        st.success("Dati caricati correttamente!")
        st.rerun()
    else:
        st.warning("Nessun portafoglio trovato con questo ID.")

# Impostazioni Investimento
st.sidebar.markdown("---")
st.session_state.monthly_investment = st.sidebar.number_input(
    "Investimento Mensile Totale (€)", min_value=0.0, value=float(st.session_state.monthly_investment)
)

# Aggiunta Asset
with st.sidebar.expander("➕ Aggiungi nuovo ETF"):
    new_ticker = st.text_input("Ticker (es: SWDA.MI)")
    new_weight = st.slider("Allocazione (%)", 0, 100, 10)
    if st.button("Aggiungi"):
        if new_ticker:
            with st.spinner("Cercando..."):
                try:
                    info = yf.Ticker(new_ticker).info
                    st.session_state.portfolio[new_ticker.upper()] = {
                        'Nome': info.get('longName', new_ticker),
                        'Peso': new_weight,
                        'Prezzo': info.get('previousClose', 0.0)
                    }
                    st.rerun()
                except:
                    st.error("Ticker non trovato.")

# --- DISPLAY E MODIFICA ---
if st.session_state.portfolio:
    st.subheader(f"Portafoglio: {portfolio_id}")
    
    total_weight = 0
    to_delete = []

    # Tabella interattiva
    for ticker, info in st.session_state.portfolio.items():
        col1, col2, col3, col4, col5 = st.columns([3, 1, 2, 2, 1])
        
        col1.write(f"**{info['Nome']}**")
        col2.code(ticker)
        
        # Modifica percentuale
        new_p = col3.number_input(f"Peso %", 0, 100, int(info['Peso']), key=f"p_{ticker}")
        st.session_state.portfolio[ticker]['Peso'] = new_p
        total_weight += new_p
        
        # Calcolo Euro
        euro_val = (new_p / 100) * st.session_state.monthly_investment
        col4.write(f"{euro_val:,.2f} €")
        
        if col5.button("🗑️", key=f"del_{ticker}"):
            to_delete.append(ticker)

    # Rimozione differita
    for t in to_delete:
        del st.session_state.portfolio[t]
        st.rerun()

    # Barra di controllo totale
    st.markdown("---")
    if total_weight > 100:
        st.error(f"Errore: Totale {total_weight}% (supera 100%)")
    else:
        st.info(f"Totale allocato: {total_weight}% | Rimanente: {100-total_weight}%")

    # BOTTONE SALVATAGGIO
    if st.button("💾 SALVA MODIFICHE NEL CLOUD"):
        save_to_cloud(portfolio_id, st.session_state.portfolio, st.session_state.monthly_investment)

    # GRAFICI
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        df_plot = pd.DataFrame([{'ETF': k, 'Peso': v['Peso']} for k, v in st.session_state.portfolio.items()])
        fig = px.pie(df_plot, values='Peso', names='ETF', hole=0.4, title="Asset Allocation")
        st.plotly_chart(fig)
    
    with col_chart2:
        if st.button("📈 Mostra Performance Storica"):
            tickers = list(st.session_state.portfolio.keys())
            hist = yf.download(tickers, period="1y")['Close'].ffill()
            norm = (hist / hist.iloc[0]) * 100
            port_perf = sum(norm[t] * (st.session_state.portfolio[t]['Peso']/100) for t in tickers)
            st.line_chart(port_perf)

else:
    st.info("Configura Supabase e carica un portafoglio o creane uno nuovo.")