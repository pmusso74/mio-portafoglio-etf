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
st.set_page_config(page_title="ETF Monitor", layout="wide")

if 'portfolio' not in st.session_state: st.session_state.portfolio = {}
if 'm_inv' not in st.session_state: st.session_state.m_inv = 1000.0
if 'loaded' not in st.session_state: st.session_state.loaded = False

# --- INTERFACCIA: ACCESSO ---
st.title("🌐 ETF Cloud Monitor")
user_id = st.text_input("🔑 ID Personale per sincronizzare", placeholder="Inserisci il tuo ID e premi Invio")

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
    st.info("👋 Inserisci un ID in alto per caricare i tuoi dati.")
    st.stop()

# Budget Sezione
col_b1, col_b2 = st.columns(2)
with col_b1:
    st.session_state.m_inv = st.number_input("💰 Investimento Mensile Totale (€)", value=float(st.session_state.m_inv), step=50.0)
with col_b2:
    w_inv_total = (st.session_state.m_inv * 12) / 52
    st.metric("📅 Equivalente Settimanale", f"{w_inv_total:.2f} €")

# LISTA ETF
if st.session_state.portfolio:
    st.subheader("📋 Il tuo Portafoglio")
    
    total_weight = 0
    to_delete = []
    
    # Intestazioni
    cols = st.columns([2.5, 1, 1.5, 1.5, 1.5, 0.5])
    cols[0].write("**Nome ETF**"); cols[1].write("**Prezzo**"); cols[2].write("**Peso %**")
    cols[3].write("**Mensile**"); cols[4].write("**Settim.**"); cols[5].write("**Az.**")

    for t, info in list(st.session_state.portfolio.items()):
        c1, c2, c3, c4, c5, c6 = st.columns([2.5, 1, 1.5, 1.5, 1.5, 0.5])
        c1.write(f"**{info['nome']}**\n({t})")
        c2.write(f"{info['prezzo']:.2f}€")
        
        # Modifica Peso
        new_p = c3.number_input("%", 0, 100, int(info['peso']), key=f"w_{t}")
        if new_p != info['peso']:
            st.session_state.portfolio[t]['peso'] = new_p
            trigger_autosave()
        total_weight += new_p
        
        m_euro = (new_p / 100) * st.session_state.m_inv
        w_euro = (m_euro * 12) / 52
        c4.write(f"{m_euro:,.2f}€")
        c5.write(f"{w_euro:,.2f}€")
        
        if c6.button("🗑️", key=f"del_{t}"):
            del st.session_state.portfolio[t]
            trigger_autosave(); st.rerun()

    st.divider()
    if total_weight != 100: st.warning(f"Allocazione attuale: {total_weight}%")
    else: st.success("Allocazione ottimale: 100%")

    # --- GRAFICO STORICO (SOTTO GLI ETF) ---
    st.subheader("📈 Andamento Storico (Ultimi 12 mesi)")
    if st.button("Aggiorna Grafico Performance"):
        with st.spinner("Scaricamento dati..."):
            try:
                tickers = list(st.session_state.portfolio.keys())
                # Scarichiamo i dati Close
                raw_data = yf.download(tickers, period="1y", interval="1d")['Close']
                
                # Pulizia dati: Se un solo ticker, yf restituisce una Series, convertiamola in DataFrame
                if isinstance(raw_data, pd.Series):
                    df_prices = raw_data.to_frame()
                    df_prices.columns = tickers
                else:
                    df_prices = raw_data

                # Normalizzazione (Base 100) e gestione dati mancanti
                df_prices = df_prices.ffill().bfill()
                norm_data = (df_prices / df_prices.iloc[0]) * 100
                
                # Calcolo portafoglio pesato
                portfolio_perf = pd.Series(0.0, index=norm_data.index)
                for t in tickers:
                    weight = st.session_state.portfolio[t]['peso'] / 100
                    portfolio_perf += norm_data[t] * weight
                
                # Creazione Grafico
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=portfolio_perf.index, y=portfolio_perf, 
                                         name="IL MIO PORTAFOGLIO", 
                                         line=dict(color='#00FF00', width=4)))
                
                for t in tickers:
                    fig.add_trace(go.Scatter(x=norm_data.index, y=norm_data[t], 
                                             name=f"Indice {t}", opacity=0.4, line=dict(dash='dot')))
                
                fig.update_layout(
                    title="Evoluzione di 100€ investiti (Media Pesata)",
                    xaxis_title="Data", yaxis_title="Valore Relativo (Base 100)",
                    hovermode="x unified", template="plotly_dark",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Errore nel caricamento del grafico: {e}")
else:
    st.info("Portafoglio vuoto. Aggiungi asset dalla barra laterale.")
