import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

# --- CONFIGURAZIONE STORAGE CLOUD ---
STORAGE_API = "https://kvdb.io/S5vYV9hPZ6f7v8k1S2v3v4/" 

def cloud_save(user_id, data):
    try: requests.post(f"{STORAGE_API}{user_id}", json=data)
    except: pass

def cloud_load(user_id):
    try:
        response = requests.get(f"{STORAGE_API}{user_id}")
        if response.status_code == 200: return response.json()
    except: return None
    return None

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF Cloud Monitor", layout="wide")

if 'portfolio' not in st.session_state: st.session_state.portfolio = {}
if 'm_inv' not in st.session_state: st.session_state.m_inv = 1000.0
if 'loaded' not in st.session_state: st.session_state.loaded = False

# --- INTERFACCIA: ACCESSO ---
st.title("🌐 ETF Cloud Monitor & Performance")
user_id = st.text_input("🔑 ID Personale per sincronizzare", placeholder="Es: mio_portafoglio_segreto")

if user_id and not st.session_state.loaded:
    data = cloud_load(user_id)
    if data:
        st.session_state.portfolio = data.get('portfolio', {})
        st.session_state.m_inv = data.get('m_inv', 1000.0)
        st.session_state.loaded = True
        st.rerun()

def trigger_autosave():
    if user_id:
        cloud_save(user_id, {"portfolio": st.session_state.portfolio, "m_inv": st.session_state.m_inv})

# --- SIDEBAR: AGGIUNTA ---
with st.sidebar:
    st.header("➕ Aggiungi ETF")
    query = st.text_input("Ticker o ISIN", placeholder="es: SWDA.MI")
    if st.button("Aggiungi"):
        if query:
            try:
                info = yf.Ticker(query).info
                st.session_state.portfolio[query.upper()] = {
                    "nome": info.get('longName', query.upper()),
                    "peso": 10,
                    "prezzo": info.get('previousClose', 0.0)
                }
                trigger_autosave()
                st.rerun()
            except: st.error("Non trovato.")

# --- AREA PRINCIPALE ---
if not user_id:
    st.info("Inserisci un ID in alto per caricare i tuoi dati.")
    st.stop()

st.session_state.m_inv = st.number_input("💰 Investimento Mensile Totale (€)", value=float(st.session_state.m_inv))

if st.session_state.portfolio:
    tab1, tab2 = st.tabs(["📋 Gestione Portafoglio", "📈 Andamento Storico"])

    with tab1:
        total_weight = 0
        to_delete = []
        
        # Header Tabella
        cols = st.columns([3, 1, 2, 2, 1])
        cols[0].write("**Nome**"); cols[1].write("**Prezzo**"); cols[2].write("**Peso %**"); cols[3].write("**Euro**")

        for t, info in list(st.session_state.portfolio.items()):
            c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 2, 1])
            c1.write(f"{info['nome']}\n({t})")
            c2.write(f"{info['prezzo']:.2f}€")
            
            new_p = c3.number_input("%", 0, 100, int(info['peso']), key=f"w_{t}")
            if new_p != info['peso']:
                st.session_state.portfolio[t]['peso'] = new_p
                trigger_autosave()
            
            total_weight += new_p
            c4.write(f"**{(new_p/100)*st.session_state.m_inv:,.2f} €**")
            if c5.button("🗑️", key=f"del_{t}"):
                del st.session_state.portfolio[t]
                trigger_autosave(); st.rerun()

        st.divider()
        if total_weight != 100: st.warning(f"Allocazione totale: {total_weight}%")
        else: st.success("Allocazione 100%")

    with tab2:
        st.subheader("Andamento del Portafoglio (Ultimi 12 mesi)")
        if st.button("🚀 Genera/Aggiorna Grafico"):
            with st.spinner("Scaricamento dati storici..."):
                tickers = list(st.session_state.portfolio.keys())
                # Scarichiamo i dati dell'ultimo anno
                data = yf.download(tickers, period="1y")['Close']
                
                if len(tickers) == 1:
                    data = data.to_frame()
                    data.columns = tickers

                # Normalizzazione a base 100 (tutto parte da 100)
                norm_data = (data / data.iloc[0]) * 100
                
                # Calcolo del portafoglio pesato
                portfolio_perf = pd.Series(0, index=norm_data.index)
                for t in tickers:
                    peso = st.session_state.portfolio[t]['peso'] / 100
                    portfolio_perf += norm_data[t] * peso
                
                # Creazione Grafico con Plotly
                fig_perf = go.Figure()
                
                # Traccia Portafoglio
                fig_perf.add_trace(go.Scatter(x=portfolio_perf.index, y=portfolio_perf, 
                                             name="MIO PORTAFOGLIO", 
                                             line=dict(color='gold', width=4)))
                
                # Tracce singoli ETF (opzionali, più trasparenti)
                for t in tickers:
                    fig_perf.add_trace(go.Scatter(x=norm_data.index, y=norm_data[t], 
                                                 name=t, opacity=0.3, line=dict(dash='dot')))
                
                fig_perf.update_layout(
                    title="Performance ipotetica di 100€ investiti 1 anno fa",
                    xaxis_title="Data",
                    yaxis_title="Valore (Base 100)",
                    hovermode="x unified"
                )
                st.plotly_chart(fig_perf, use_container_width=True)
                
                st.caption("Il grafico mostra come si sarebbe evoluto un investimento iniziale di 100€ suddiviso secondo le tue attuali percentuali.")

else:
    st.info("Aggiungi ETF per iniziare.")
