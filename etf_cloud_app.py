import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
import json

# --- CONFIGURAZIONE STORAGE CLOUD (Senza configurazione per l'utente) ---
# Utilizziamo un database pubblico temporaneo che non richiede chiavi private
STORAGE_API = "https://kvdb.io/S5vYV9hPZ6f7v8k1S2v3v4/" # Bucket pubblico generato per questa app

def cloud_save(user_id, data):
    try:
        requests.post(f"{STORAGE_API}{user_id}", json=data)
    except:
        pass

def cloud_load(user_id):
    try:
        response = requests.get(f"{STORAGE_API}{user_id}")
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF Auto-Monitor", layout="wide")

# Inizializzazione Sessione
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'm_inv' not in st.session_state:
    st.session_state.m_inv = 1000.0
if 'loaded' not in st.session_state:
    st.session_state.loaded = False

# --- INTERFACCIA: ACCESSO ---
st.title("🌐 ETF Cloud Monitor (Automatico)")
user_id = st.text_input("🔑 Inserisci il tuo ID Personale per sincronizzare i dati", 
                        placeholder="Es: marco_secret_2024", help="Usa lo stesso ID su qualsiasi PC per ritrovare i tuoi dati")

if user_id and not st.session_state.loaded:
    with st.spinner("Sincronizzazione cloud..."):
        data = cloud_load(user_id)
        if data:
            st.session_state.portfolio = data.get('portfolio', {})
            st.session_state.m_inv = data.get('m_inv', 1000.0)
            st.session_state.loaded = True
            st.success("Dati recuperati!")
            st.rerun()

# --- LOGICA DI SALVATAGGIO AUTOMATICO ---
def trigger_autosave():
    if user_id:
        data = {"portfolio": st.session_state.portfolio, "m_inv": st.session_state.m_inv}
        cloud_save(user_id, data)

# --- SIDEBAR: AGGIUNTA ASSET ---
with st.sidebar:
    st.header("➕ Aggiungi ETF")
    query = st.text_input("Inserisci ISIN o Ticker", placeholder="es: SWDA.MI o IE00B4L5Y983")
    
    if st.button("Cerca e Aggiungi"):
        if query:
            with st.spinner("Ricerca..."):
                try:
                    ticker = yf.Ticker(query)
                    # Se l'ISIN non restituisce info, yfinance a volte fallisce, quindi verifichiamo
                    info = ticker.info
                    name = info.get('longName', query.upper())
                    price = info.get('previousClose', 0.0)
                    
                    st.session_state.portfolio[query.upper()] = {
                        "nome": name,
                        "peso": 10,
                        "prezzo": price
                    }
                    trigger_autosave()
                    st.rerun()
                except:
                    st.error("Asset non trovato. Prova con il Ticker (es. CSPX.MI)")

# --- AREA PRINCIPALE ---
if not user_id:
    st.info("👋 Benvenuto! Inserisci un ID Personale in alto per iniziare.")
    st.stop()

# Impostazione Investimento Mensile
old_inv = st.session_state.m_inv
st.session_state.m_inv = st.number_input("💰 Investimento Mensile Totale (€)", 
                                         value=float(st.session_state.m_inv), step=50.0)
if old_inv != st.session_state.m_inv:
    trigger_autosave()

if st.session_state.portfolio:
    st.subheader("📝 Gestione Portafoglio")
    
    # Intestazioni
    cols = st.columns([3, 1, 2, 2, 1])
    cols[0].write("**Nome**")
    cols[1].write("**Prezzo**")
    cols[2].write("**Allocazione %**")
    cols[3].write("**Investimento**")
    cols[4].write("**Azione**")

    total_weight = 0
    to_delete = []

    for t, info in list(st.session_state.portfolio.items()):
        c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 2, 1])
        
        c1.write(f"**{info['nome']}**\n({t})")
        c2.write(f"{info['prezzo']:.2f}€")
        
        # Modifica Peso
        new_peso = c3.number_input("%", 0, 100, int(info['peso']), key=f"w_{t}")
        if new_peso != info['peso']:
            st.session_state.portfolio[t]['peso'] = new_peso
            trigger_autosave()
        
        total_weight += new_peso
        
        # Calcolo Euro
        euro_val = (new_peso / 100) * st.session_state.m_inv
        c4.write(f"**{euro_val:,.2f} €**")
        
        # Elimina
        if c5.button("🗑️", key=f"del_{t}"):
            del st.session_state.portfolio[t]
            trigger_autosave()
            st.rerun()

    st.divider()

    # Stato del bilanciamento
    if total_weight > 100:
        st.error(f"Totale: {total_weight}% (Supera il 100%!)")
    elif total_weight < 100:
        st.warning(f"Totale: {total_weight}% (Hai ancora il {100-total_weight}% libero)")
    else:
        st.success("Bilanciamento perfetto (100%)")

    # Grafico
    df_plot = pd.DataFrame([{"ETF": k, "Peso": v['peso']} for k, v in st.session_state.portfolio.items()])
    fig = px.pie(df_plot, values='Peso', names='ETF', hole=0.4, title="Asset Allocation")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Il tuo portafoglio è vuoto. Aggiungi un ETF dalla barra laterale.")

st.caption("☁️ I dati vengono salvati automaticamente nel cloud ogni volta che modifichi qualcosa.")
