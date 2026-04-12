import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF Auto-Cloud Monitor", layout="wide")

# --- CONNESSIONE E AUTO-SETUP ---
st.sidebar.title("🔐 Accesso Cloud")
sb_url = st.sidebar.text_input("Supabase URL")
sb_key = st.sidebar.text_input("Supabase Service Role Key (Secret)", type="password")

def run_sql(sql_query):
    """Esegue SQL su Supabase tramite REST API"""
    url = f"{sb_url}/rest/v1/"
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    # Nota: Supabase non espone direttamente l'esecuzione SQL via REST per sicurezza 
    # di default, quindi usiamo un trucco: se la tabella non esiste, proviamo a crearla
    # tramite una chiamata rpc o segnaliamo l'istruzione.
    pass

def init_app():
    """Inizializza lo stato dell'app"""
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = {}
    if 'm_inv' not in st.session_state:
        st.session_state.m_inv = 1000.0

init_app()

# --- FUNZIONI DATABASE ---
def cloud_sync(action="load", p_id="default"):
    if not sb_url or not sb_key:
        st.warning("Inserisci le chiavi Supabase nella barra laterale.")
        return
    
    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}", "Content-Type": "application/json"}
    table_url = f"{sb_url}/rest/v1/portfolios"

    if action == "save":
        data = {
            "id": p_id,
            "data": st.session_state.portfolio,
            "monthly_investment": st.session_state.m_inv
        }
        res = requests.post(table_url, json=data, headers={**headers, "Prefer": "resolution=merge-duplicates"})
        if res.status_code in [200, 201]:
            st.success("☁️ Salvataggio completato!")
        else:
            st.error(f"Errore: Assicurati di aver creato la tabella. Log: {res.text}")

    elif action == "load":
        res = requests.get(f"{table_url}?id=eq.{p_id}", headers=headers)
        if res.status_code == 200 and res.json():
            item = res.json()[0]
            st.session_state.portfolio = item['data']
            st.session_state.m_inv = item['monthly_investment']
            st.sidebar.success("✅ Portafoglio Caricato!")
            st.rerun()
        else:
            st.sidebar.error("Portafoglio non trovato o tabella mancante.")

# --- INTERFACCIA UTENTE ---
st.title("📈 ETF Portfolio Cloud Manager")

# Setup ID
p_id = st.text_input("👤 Inserisci il tuo ID Portafoglio (es: mio_nome_2024)", "default_user")

col_btn1, col_btn2 = st.columns(2)
if col_btn1.button("📂 Carica dal Cloud"):
    cloud_sync("load", p_id)

# Sezione Aiuto per Tabella
with st.expander("🛠️ Se il caricamento fallisce (Primo Setup)"):
    st.write("Se è la prima volta che usi Supabase, devi creare la tabella. Copia questo codice e incollalo nel tasto 'SQL Editor' di Supabase:")
    st.code(f"""
    create table portfolios (
      id text primary key,
      data jsonb,
      monthly_investment float
    );
    alter table portfolios disable row level security;
    """, language="sql")

st.divider()

# Input Investimento
st.session_state.m_inv = st.number_input("💰 Investimento Mensile Totale (€)", value=float(st.session_state.m_inv), step=50.0)

# Aggiunta ETF
with st.sidebar.expander("➕ Aggiungi Asset", expanded=True):
    ticker_in = st.text_input("Ticker o ISIN (es: SWDA.MI, VUSA.L)")
    weight_in = st.slider("Allocazione iniziale (%)", 0, 100, 10)
    if st.button("Aggiungi al Portafoglio"):
        if ticker_in:
            with st.spinner("Recupero dati..."):
                try:
                    name = yf.Ticker(ticker_in).info.get('longName', ticker_in)
                    st.session_state.portfolio[ticker_in.upper()] = {"nome": name, "peso": weight_in}
                    st.rerun()
                except:
                    st.error("Ticker non trovato.")

# Gestione Asset
if st.session_state.portfolio:
    st.subheader("📝 Il tuo Portafoglio")
    
    total_w = 0
    to_delete = []

    for t, info in st.session_state.portfolio.items():
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        c1.write(f"**{info['nome']}** ({t})")
        
        # Modifica Percentuale
        new_w = c2.number_input(f"Peso %", 0, 100, int(info['peso']), key=f"w_{t}")
        st.session_state.portfolio[t]['peso'] = new_w
        total_w += new_w
        
        # Calcolo Euro
        c3.write(f"**{(new_w/100)*st.session_state.m_inv:.2f} €**")
        
        if c4.button("🗑️", key=f"del_{t}"):
            to_delete.append(t)

    for t in to_delete:
        del st.session_state.portfolio[t]
        st.rerun()

    st.divider()
    
    # Barra di controllo
    if total_w > 100:
        st.error(f"ATTENZIONE: Il totale è {total_w}%. Riduci le percentuali!")
    elif total_w < 100:
        st.warning(f"Totale allocato: {total_w}% (Manca il {100-total_w}%)")
    else:
        st.success("Ottimo! Il totale è 100%")

    if st.button("💾 SALVA TUTTO NEL CLOUD"):
        cloud_sync("save", p_id)

    # Grafico
    df_plot = pd.DataFrame([{"Asset": k, "Peso": v['peso']} for k, v in st.session_state.portfolio.items()])
    import plotly.express as px
    fig = px.pie(df_plot, values='Peso', names='Asset', hole=0.4, title="Distribuzione Portafoglio")
    st.plotly_chart(fig)
else:
    st.info("Aggiungi un ETF per iniziare.")
