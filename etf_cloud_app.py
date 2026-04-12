import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="ETF Portfolio Pro", layout="wide")

# Inizializzazione Sessione (Per non perdere i dati durante i click)
if 'df_portfolio' not in st.session_state:
    st.session_state.df_portfolio = pd.DataFrame(columns=['Ticker', 'Nome', 'Allocazione %', 'Prezzo (€)'])

if 'monthly_inv' not in st.session_state:
    st.session_state.monthly_inv = 1000.0

# --- FUNZIONI CLOUD ---
def save_to_cloud(bin_id, api_key):
    url = f"https://api.jsonbin.io/v3/b/{bin_id}"
    headers = {"Content-Type": "application/json", "X-Master-Key": api_key}
    data = {
        "portfolio": st.session_state.df_portfolio.to_dict('records'),
        "monthly_inv": st.session_state.monthly_inv
    }
    res = requests.put(url, json=data, headers=headers)
    if res.status_code == 200:
        st.success("✅ Salvato nel Cloud!")
    else:
        st.error("❌ Errore durante il salvataggio.")

def load_from_cloud(bin_id, api_key):
    url = f"https://api.jsonbin.io/v3/b/{bin_id}/latest"
    headers = {"X-Master-Key": api_key}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()['record']
        st.session_state.df_portfolio = pd.DataFrame(data['portfolio'])
        st.session_state.monthly_inv = data['monthly_inv']
        st.success("📂 Portafoglio caricato!")
        st.rerun()
    else:
        st.error("❌ Impossibile caricare i dati.")

# --- INTERFACCIA ---
st.title("📊 Gestore ETF Professionale")

# Sidebar per Cloud
with st.sidebar:
    st.header("☁️ Sincronizzazione Cloud")
    api_key = st.text_input("JSONBin API Key", type="password")
    bin_id = st.text_input("JSONBin Bin ID")
    
    col1, col2 = st.columns(2)
    if col1.button("💾 Salva"): save_to_cloud(bin_id, api_key)
    if col2.button("📂 Carica"): load_from_cloud(bin_id, api_key)
    
    st.divider()
    st.header("➕ Aggiungi Asset")
    new_ticker = st.text_input("ISIN o Ticker (es: SWDA.MI)")
    if st.button("Cerca e Aggiungi"):
        try:
            ticker_data = yf.Ticker(new_ticker)
            name = ticker_data.info.get('longName', new_ticker)
            price = ticker_data.info.get('previousClose', 0.0)
            
            new_row = pd.DataFrame([{
                'Ticker': new_ticker.upper(),
                'Nome': name,
                'Allocazione %': 0,
                'Prezzo (€)': price
            }])
            st.session_state.df_portfolio = pd.concat([st.session_state.df_portfolio, new_row], ignore_index=True)
            st.rerun()
        except:
            st.error("Asset non trovato su Yahoo Finance.")

# --- AREA PRINCIPALE ---
st.session_state.monthly_inv = st.number_input("Investimento Mensile Totale (€)", value=float(st.session_state.monthly_inv))

if not st.session_state.df_portfolio.empty:
    st.subheader("Il tuo Portafoglio")
    st.write("💡 *Puoi modificare le percentuali e il ticker direttamente nella tabella. Per eliminare un asset, seleziona la riga e premi CANC.*")

    # TABELLA INTERATTIVA (Il cuore dell'app)
    edited_df = st.data_editor(
        st.session_state.df_portfolio,
        num_rows="dynamic", # Permette di aggiungere/rimuovere righe manualmente
        use_container_width=True,
        column_config={
            "Allocazione %": st.column_config.NumberColumn(format="%d%%", min_value=0, max_value=100),
            "Prezzo (€)": st.column_config.NumberColumn(format="%.2f €", disabled=True),
        }
    )
    
    # Aggiorna lo stato con i dati modificati
    st.session_state.df_portfolio = edited_df

    # Calcoli
    total_alloc = st.session_state.df_portfolio['Allocazione %'].sum()
    
    # Calcolo Euro per ogni riga
    st.divider()
    st.subheader("Resoconto Investimento")
    
    resoconto = st.session_state.df_portfolio.copy()
    resoconto['Budget (€)'] = (resoconto['Allocazione %'] / 100) * st.session_state.monthly_inv
    resoconto['Quote (stimate)'] = resoconto['Budget (€)'] / resoconto['Prezzo (€)']
    
    st.table(resoconto[['Ticker', 'Allocazione %', 'Budget (€)', 'Quote (stimate)']].style.format({
        'Budget (€)': '{:.2f} €',
        'Quote (stimate)': '{:.4f}'
    }))

    # Validazione
    if total_alloc > 100:
        st.error(f"⚠️ Il totale delle percentuali è {total_alloc}%. Deve essere 100%.")
    elif total_alloc < 100:
        st.warning(f"Il totale è {total_alloc}%. Hai ancora {100-total_alloc}% da allocare.")
    else:
        st.success("✅ Portafoglio bilanciato al 100%.")

    # Grafico
    import plotly.express as px
    fig = px.pie(resoconto, values='Allocazione %', names='Ticker', hole=0.4)
    st.plotly_chart(fig)

else:
    st.info("Aggiungi il tuo primo ETF dalla barra laterale per iniziare.")
