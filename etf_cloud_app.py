import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="ETF Auto-Sync Monitor", layout="wide")

# --- FUNZIONI CLOUD (REDIS) ---
def cloud_execute(command, key=None, value=None):
    url = st.sidebar.text_input("Upstash URL", type="password")
    token = st.sidebar.text_input("Upstash Token", type="password")
    
    if not url or not token:
        return None
    
    headers = {"Authorization": f"Bearer {token}"}
    
    if command == "set":
        payload = json.dumps(value)
        requests.post(f"{url}/set/{key}", data=payload, headers=headers)
    elif command == "get":
        res = requests.get(f"{url}/get/{key}", headers=headers).json()
        return json.loads(res['result']) if res.get('result') else None

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'monthly_inv' not in st.session_state:
    st.session_state.monthly_inv = 1000.0

# --- SIDEBAR: GESTIONE CLOUD ---
st.sidebar.title("☁️ Sincronizzazione")
user_id = st.sidebar.text_input("Il tuo ID Portafoglio (es: marco_99)", "default_user")

col_s1, col_s2 = st.sidebar.columns(2)
if col_s1.button("📂 Carica Cloud"):
    data = cloud_execute("get", user_id)
    if data:
        st.session_state.portfolio = data['portfolio']
        st.session_state.monthly_inv = data['monthly_inv']
        st.sidebar.success("Caricato!")
        st.rerun()
    else:
        st.sidebar.error("ID non trovato")

if col_s2.button("💾 Salva Cloud"):
    to_save = {"portfolio": st.session_state.portfolio, "monthly_inv": st.session_state.monthly_inv}
    cloud_execute("set", user_id, to_save)
    st.sidebar.success("Salvato!")

st.sidebar.divider()

# --- AGGIUNTA ETF ---
st.sidebar.subheader("➕ Aggiungi ETF")
isin_ticker = st.sidebar.text_input("Inserisci Ticker o ISIN (es: SWDA.MI)")
if st.sidebar.button("Cerca e Aggiungi"):
    with st.spinner("Ricerca in corso..."):
        try:
            ticker = yf.Ticker(isin_ticker)
            name = ticker.info.get('longName', isin_ticker)
            price = ticker.info.get('previousClose', 0.0)
            st.session_state.portfolio[isin_ticker.upper()] = {
                "nome": name,
                "peso": 0,
                "prezzo": price
            }
            st.rerun()
        except:
            st.error("Asset non trovato. Usa i ticker di Yahoo Finance (es: CSPX.MI)")

# --- INTERFACCIA PRINCIPALE ---
st.title("📊 Monitor ETF Multi-PC")

# Input Investimento
st.session_state.monthly_inv = st.number_input("Budget Mensile Totale (€)", value=float(st.session_state.monthly_inv), step=50.0)

if st.session_state.portfolio:
    st.subheader("Configurazione Asset")
    
    # Intestazioni Tabella
    h1, h2, h3, h4, h5 = st.columns([3, 1, 2, 2, 1])
    h1.write("**Nome**")
    h2.write("**Prezzo**")
    h3.write("**Allocazione %**")
    h4.write("**Investimento (€)**")
    h5.write("**Azione**")
    
    total_weight = 0
    to_delete = []

    # Riga per ogni ETF
    for ticker, info in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 2, 1])
        
        c1.write(f"{info['nome']} \n ({ticker})")
        c2.write(f"{info['prezzo']:.2f} €")
        
        # MODIFICA PERCENTUALE (Totalmente Interattiva)
        new_w = c3.number_input("Peso %", 0, 100, int(info['peso']), key=f"w_{ticker}")
        st.session_state.portfolio[ticker]['peso'] = new_w
        total_weight += new_w
        
        # CALCOLO EURO
        euro_amount = (new_w / 100) * st.session_state.monthly_inv
        c4.write(f"**{euro_amount:,.2f} €**")
        
        # ELIMINA ASSET
        if c5.button("🗑️", key=f"del_{ticker}"):
            to_delete.append(ticker)

    # Rimozione
    if to_delete:
        for t in to_delete:
            del st.session_state.portfolio[t]
        st.rerun()

    st.divider()

    # Barra di Stato
    if total_weight > 100:
        st.error(f"Errore: Il totale è {total_weight}%. Riduci di {total_weight-100}%")
    elif total_weight < 100:
        st.warning(f"Totale allocato: {total_weight}% (Manca il {100-total_weight}% per raggiungere il budget)")
    else:
        st.success("Portafoglio bilanciato correttamente (100%)")

    # Grafico riassuntivo
    if total_weight > 0:
        import plotly.express as px
        df = pd.DataFrame([{"Asset": k, "Peso": v['peso']} for k, v in st.session_state.portfolio.items() if v['peso'] > 0])
        fig = px.pie(df, values='Peso', names='Asset', hole=0.4, title="Distribuzione del tuo capitale")
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👈 Inizia aggiungendo un ETF dalla barra laterale. Poi salva nel cloud per vederlo su altri PC.")

# Istruzioni in basso
with st.expander("ℹ️ Come usare su altri PC"):
    st.write("""
    1. Apri questo script su un altro PC.
    2. Inserisci lo stesso **URL** e **Token** di Upstash nella barra laterale.
    3. Inserisci lo stesso **ID Portafoglio**.
    4. Clicca su **Carica Cloud**.
    """)
