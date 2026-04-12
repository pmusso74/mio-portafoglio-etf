import streamlit as st
import yfinance as yf
import pandas as pd
from supabase import create_client

# --- CONNESSIONE ---
st.sidebar.header("🔌 Connessione Cloud")
url = st.sidebar.text_input("Supabase URL")
key = st.sidebar.text_input("Supabase Anon Key", type="password")

def get_db():
    if url and key:
        try:
            return create_client(url, key)
        except Exception as e:
            st.error(f"Errore connessione: {e}")
    return None

# --- FUNZIONI CORE ---
def save_data(p_id, p_dict, m_inv):
    db = get_db()
    if db:
        try:
            # Prepariamo i dati
            row = {"id": p_id, "data": p_dict, "monthly_investment": m_inv}
            # Usiamo upsert: se l'ID esiste aggiorna, altrimenti inserisce
            response = db.table("portfolios").upsert(row).execute()
            st.sidebar.success("✅ Salvato con successo!")
        except Exception as e:
            st.sidebar.error(f"❌ Errore durante il salvataggio: {e}")

def load_data(p_id):
    db = get_db()
    if db:
        try:
            response = db.table("portfolios").select("*").eq("id", p_id).execute()
            if response.data:
                return response.data[0]
            else:
                st.sidebar.warning("Nessun portafoglio trovato con questo ID.")
        except Exception as e:
            st.sidebar.error(f"❌ Errore nel caricamento: {e}")
    return None

# --- INTERFACCIA ---
st.title("🚀 Cloud ETF Monitor")

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'm_inv' not in st.session_state:
    st.session_state.m_inv = 1000.0

# Sidebar Accesso
p_id = st.sidebar.text_input("ID Portafoglio (es: marco77)", "default")

if st.sidebar.button("📂 Carica Portafoglio"):
    res = load_data(p_id)
    if res:
        st.session_state.portfolio = res['data']
        st.session_state.m_inv = res['monthly_investment']
        st.rerun()

# Input investimento
st.session_state.m_inv = st.sidebar.number_input("Investimento Mensile (€)", value=float(st.session_state.m_inv))

# Aggiunta ETF
with st.sidebar.expander("➕ Aggiungi ETF"):
    t_input = st.text_input("Ticker (es: SWDA.MI)")
    w_input = st.slider("Peso %", 0, 100, 10)
    if st.button("Inserisci"):
        if t_input:
            st.session_state.portfolio[t_input.upper()] = {
                'Peso': w_input,
                'Nome': t_input.upper() # Per velocità usiamo il ticker come nome
            }
            st.rerun()

# Gestione Portafoglio
if st.session_state.portfolio:
    st.write(f"### Portafoglio: `{p_id}`")
    
    total_w = 0
    to_del = []
    
    for t, info in st.session_state.portfolio.items():
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        c1.write(f"**{t}**")
        new_w = c2.number_input("%", 0, 100, int(info['Peso']), key=f"w_{t}")
        st.session_state.portfolio[t]['Peso'] = new_w
        total_w += new_w
        c3.write(f"{(new_w/100)*st.session_state.m_inv:.2f} €")
        if c4.button("🗑️", key=f"del_{t}"):
            to_del.append(t)
            
    for t in to_del:
        del st.session_state.portfolio[t]
        st.rerun()

    st.warning(f"Totale allocato: {total_w}%")

    if st.button("💾 SALVA NEL CLOUD"):
        save_data(p_id, st.session_state.portfolio, st.session_state.m_inv)
else:
    st.info("Portafoglio vuoto. Aggiungi un ETF o carica dal cloud.")
