import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import json
import base64

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="ETF Portfolio Monitor", layout="wide")

# Inizializzazione dati
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'monthly_inv' not in st.session_state:
    st.session_state.monthly_inv = 1000.0

# --- FUNZIONI DI BACKUP (Per Multi-PC senza database) ---
def get_backup_code():
    data = {"p": st.session_state.portfolio, "m": st.session_state.monthly_inv}
    json_str = json.dumps(data)
    return base64.b64encode(json_str.encode()).decode()

def load_backup_code(code):
    try:
        decoded = base64.b64decode(code.encode()).decode()
        data = json.loads(decoded)
        st.session_state.portfolio = data["p"]
        st.session_state.monthly_inv = data["m"]
        st.success("✅ Portafoglio caricato correttamente!")
    except:
        st.error("❌ Codice non valido")

# --- INTERFACCIA ---
st.title("📊 Monitor Portafoglio ETF")

# Sidebar: Aggiunta e Backup
with st.sidebar:
    st.header("➕ Aggiungi ETF")
    new_ticker = st.text_input("Ticker o ISIN (es: SWDA.MI, VUSA.L)")
    if st.button("Aggiungi Asset"):
        if new_ticker:
            with st.spinner("Ricerca in corso..."):
                try:
                    t_data = yf.Ticker(new_ticker)
                    # Prova a prendere il nome, altrimenti usa il ticker
                    name = t_data.info.get('longName', new_ticker.upper())
                    price = t_data.info.get('previousClose', 0.0)
                    
                    st.session_state.portfolio[new_ticker.upper()] = {
                        "nome": name,
                        "peso": 0,
                        "prezzo": price
                    }
                    st.success(f"Aggiunto: {new_ticker.upper()}")
                except:
                    st.error("Non trovato. Prova con il Ticker di Yahoo (es. CSPX.MI)")

    st.divider()
    st.header("💾 Sincronizza PC")
    st.write("Copia questo codice per portarlo su un altro PC:")
    st.code(get_backup_code(), language=None)
    
    import_code = st.text_area("Incolla qui il codice di un altro PC:")
    if st.button("Importa Portafoglio"):
        load_backup_code(import_code)
        st.rerun()

# --- AREA PRINCIPALE ---
st.session_state.monthly_inv = st.number_input("Investimento Mensile Totale (€)", 
                                              value=float(st.session_state.monthly_inv), step=50.0)

if st.session_state.portfolio:
    st.subheader("Asset nel Portafoglio")
    
    # Intestazione Colonne
    h1, h2, h3, h4, h5 = st.columns([3, 1, 2, 2, 1])
    h1.write("**Nome ETF**")
    h2.write("**Prezzo**")
    h3.write("**Allocazione %**")
    h4.write("**Budget (€)**")
    h5.write("**Azione**")

    total_w = 0
    to_delete = []

    # Lista Asset
    for ticker, info in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5 = st.columns([3, 1, 2, 2, 1])
        
        c1.write(f"**{info['nome']}**\n({ticker})")
        c2.write(f"{info['prezzo']:.2f}€")
        
        # Modifica percentuale (Aggiorna istantaneamente)
        new_peso = c3.number_input("%", 0, 100, int(info['peso']), key=f"w_{ticker}")
        st.session_state.portfolio[ticker]['peso'] = new_peso
        total_w += new_peso
        
        # Calcolo Euro
        euro_val = (new_peso / 100) * st.session_state.monthly_inv
        c4.write(f"**{euro_val:,.2f} €**")
        
        # Bottone Elimina
        if c5.button("🗑️", key=f"del_{ticker}"):
            to_delete.append(ticker)

    # Esecuzione eliminazione
    for t in to_delete:
        del st.session_state.portfolio[t]
        st.rerun()

    st.divider()

    # Controllo Totale
    if total_w > 100:
        st.error(f"Il totale è {total_w}%. Supera il 100%!")
    elif total_w < 100:
        st.warning(f"Totale allocato: {total_w}% (Manca il {100-total_w}%)")
    else:
        st.success("Portafoglio correttamente allocato al 100%")

    # Grafico
    if total_w > 0:
        df_plot = pd.DataFrame([{"ETF": k, "Peso": v['peso']} for k, v in st.session_state.portfolio.items()])
        fig = px.pie(df_plot, values='Peso', names='ETF', hole=0.4, title="Distribuzione Asset")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Inizia aggiungendo un ETF dal menu a sinistra.")
