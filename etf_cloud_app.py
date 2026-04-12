import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configurazione Pagina
st.set_page_config(page_title="ETF Portfolio Manager", layout="wide")

st.title("📊 ETF Portfolio Builder & Monitor")

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {} # Usiamo un dizionario {Ticker: {dati}}

# --- SIDEBAR: INPUT ---
st.sidebar.header("⚙️ Impostazioni Base")
total_monthly_investment = st.sidebar.number_input(
    "Investimento Mensile Totale (€)", min_value=0.0, value=1000.0, step=50.0
)

st.sidebar.markdown("---")
st.sidebar.subheader("➕ Aggiungi Asset")
new_ticker = st.sidebar.text_input("Inserisci Ticker o ISIN (es: SWDA.MI, CSSX5E.MI)")
new_weight = st.sidebar.slider("Allocazione iniziale (%)", 0, 100, 10)

if st.sidebar.button("Aggiungi al Portafoglio"):
    if new_ticker:
        ticker_upper = new_ticker.upper().strip()
        if ticker_upper not in st.session_state.portfolio:
            try:
                with st.spinner(f'Ricerca di {ticker_upper}...'):
                    info = yf.Ticker(ticker_upper).info
                    name = info.get('longName', ticker_upper)
                    price = info.get('previousClose', 0.0)
                    
                    st.session_state.portfolio[ticker_upper] = {
                        'Nome': name,
                        'Peso': new_weight,
                        'Prezzo': price
                    }
                    st.success(f"Aggiunto: {name}")
            except Exception as e:
                st.error("Errore: Ticker non trovato. Usa il formato Yahoo Finance (es. CSPX.MI)")
        else:
            st.warning("L'asset è già presente nel portafoglio.")

# --- AREA PRINCIPALE: GESTIONE PORTAFOGLIO ---
if st.session_state.portfolio:
    st.subheader("📝 Gestione Asset e Allocazioni")
    
    # Creiamo una lista di ticker per iterare
    tickers = list(st.session_state.portfolio.keys())
    
    # Tabella di gestione
    cols_header = st.columns([3, 2, 2, 2, 1])
    cols_header[0].write("**Nome ETF**")
    cols_header[1].write("**Ticker**")
    cols_header[2].write("**Peso (%)**")
    cols_header[3].write("**Budget (€)**")
    cols_header[4].write("**Azione**")

    total_current_weight = 0
    
    for ticker in tickers:
        asset = st.session_state.portfolio[ticker]
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
        
        c1.write(f"**{asset['Nome']}**")
        c2.code(ticker)
        
        # MODIFICA PERCENTUALE: ogni cambio aggiorna lo stato
        new_val = c3.number_input(f"Peso %", min_value=0, max_value=100, 
                                 value=int(asset['Peso']), key=f"w_{ticker}")
        st.session_state.portfolio[ticker]['Peso'] = new_val
        total_current_weight += new_val
        
        # Calcolo budget dinamico
        budget_asset = (new_val / 100) * total_monthly_investment
        c4.write(f"{budget_asset:,.2f} €")
        
        # ELIMINA ASSET
        if c5.button("🗑️", key=f"del_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    # Controllo Validazione Totale
    st.markdown("---")
    col_sum1, col_sum2 = st.columns(2)
    
    if total_current_weight > 100:
        col_sum1.error(f"ATTENZIONE: Il totale è {total_current_weight}%. Supera il 100%!")
    elif total_current_weight < 100:
        col_sum1.warning(f"Totale allocato: {total_current_weight}%. Mancano {100-total_current_weight}%")
    else:
        col_sum1.success(f"Totale allocato: {total_current_weight}% (Ottimale)")

    # --- VISUALIZZAZIONE E MONITORAGGIO ---
    if total_current_weight > 0:
        tab1, tab2 = st.tabs(["📊 Analisi Distribuzione", "📈 Andamento Storico"])
        
        with tab1:
            # Preparazione dati per grafico
            plot_data = pd.DataFrame([
                {'Nome': v['Nome'], 'Peso': v['Peso']} 
                for k, v in st.session_state.portfolio.items() if v['Peso'] > 0
            ])
            fig_pie = px.pie(plot_data, values='Peso', names='Nome', hole=0.5, 
                             title="Composizione Portafoglio Target")
            st.plotly_chart(fig_pie, use_container_width=True)

        with tab2:
            if st.button("Genera Grafico Performance"):
                with st.spinner('Scaricamento dati storici...'):
                    hist_data = yf.download(tickers, period="1y")['Close']
                    
                    # Se c'è solo un ticker, yfinance restituisce una Serie, la convertiamo in DataFrame
                    if len(tickers) == 1:
                        hist_data = hist_data.to_frame()
                        hist_data.columns = tickers

                    # Normalizzazione (Base 100)
                    norm_data = (hist_data / hist_data.iloc[0]) * 100
                    
                    # Calcolo Portafoglio Pesato
                    portfolio_sim = pd.Series(0.0, index=norm_data.index)
                    for t in tickers:
                        weight = st.session_state.portfolio[t]['Peso'] / 100
                        portfolio_sim += norm_data[t] * weight
                    
                    fig_line = go.Figure()
                    fig_line.add_trace(go.Scatter(x=portfolio_sim.index, y=portfolio_sim, 
                                                 name="MIO PORTAFOGLIO", line=dict(color='gold', width=4)))
                    
                    for t in tickers:
                        fig_line.add_trace(go.Scatter(x=norm_data.index, y=norm_data[t], 
                                                     name=t, opacity=0.4, line=dict(dash='dot')))
                    
                    fig_line.update_layout(title="Andamento Ipotetico Ultimo Anno (Base 100)",
                                          yaxis_title="Valore Relativo",
                                          hovermode="x unified")
                    st.plotly_chart(fig_line, use_container_width=True)

else:
    st.info("👈 Inizia aggiungendo un ETF (ISIN o Ticker) dalla barra laterale.")
    st.image("https://images.unsplash.com/photo-1611974717482-58a252ec074c?auto=format&fit=crop&q=80&w=1000", width=700)
