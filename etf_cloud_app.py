import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF Portfolio Manager", layout="wide", page_icon="📊")

# CSS personalizzato per migliorare l'estetica
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 ETF Portfolio Builder & Monitor")

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}

# --- SIDEBAR: INPUT ---
st.sidebar.header("⚙️ Impostazioni Base")
total_monthly_investment = st.sidebar.number_input(
    "Investimento Mensile Totale (€)", min_value=0.0, value=1000.0, step=50.0
)

st.sidebar.markdown("---")
st.sidebar.subheader("➕ Aggiungi Asset")
new_ticker = st.sidebar.text_input("Inserisci Ticker Yahoo (es: SWDA.MI, CSSX5E.MI, CSPX.L)")
new_weight = st.sidebar.slider("Allocazione desiderata (%)", 0, 100, 10)

if st.sidebar.button("Aggiungi al Portafoglio"):
    if new_ticker:
        ticker_upper = new_ticker.upper().strip()
        if ticker_upper not in st.session_state.portfolio:
            try:
                with st.spinner(f'Ricerca di {ticker_upper}...'):
                    t_info = yf.Ticker(ticker_upper)
                    # Tentativo di recupero nome
                    name = t_info.info.get('longName', ticker_upper)
                    price = t_info.info.get('previousClose', 0.0)
                    
                    if price == 0: # Se yfinance non trova info, il ticker potrebbe essere errato
                         st.error("Ticker non trovato o dati non disponibili.")
                    else:
                        st.session_state.portfolio[ticker_upper] = {
                            'Nome': name,
                            'Peso': new_weight,
                            'Prezzo': price
                        }
                        st.success(f"Aggiunto: {name}")
            except Exception as e:
                st.error(f"Errore nel recupero dati: {e}")
        else:
            st.warning("L'asset è già presente nel portafoglio.")

# --- AREA PRINCIPALE: GESTIONE PORTAFOGLIO ---
if st.session_state.portfolio:
    st.subheader("📝 Gestione Asset e Allocazioni")
    
    tickers = list(st.session_state.portfolio.keys())
    
    # Intestazioni Tabella
    cols_header = st.columns([3, 1.5, 2, 2, 1])
    cols_header[0].write("**Nome ETF**")
    cols_header[1].write("**Ticker**")
    cols_header[2].write("**Peso %**")
    cols_header[3].write("**Budget Mensile**")
    cols_header[4].write("**Azione**")

    total_current_weight = 0
    
    # Righe Asset
    for ticker in tickers:
        asset = st.session_state.portfolio[ticker]
        c1, c2, c3, c4, c5 = st.columns([3, 1.5, 2, 2, 1])
        
        c1.write(f"**{asset['Nome']}**")
        c2.code(ticker)
        
        # Input Peso
        new_val = c3.number_input(f"Peso % per {ticker}", min_value=0, max_value=100, 
                                 value=int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = new_val
        total_current_weight += new_val
        
        # Calcolo budget
        budget_asset = (new_val / 100) * total_monthly_investment
        c4.write(f"**{budget_asset:,.2f} €**")
        
        # Bottone Elimina
        if c5.button("🗑️", key=f"del_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    # --- VALIDAZIONE ---
    st.markdown("---")
    if total_current_weight > 100:
        st.error(f"⚠️ Il totale delle allocazioni è **{total_current_weight}%**. Riduci i pesi per arrivare al 100%.")
    elif total_current_weight < 100:
        st.warning(f"ℹ️ Totale allocato: **{total_current_weight}%**. Hai ancora un **{100-total_current_weight}%** da assegnare.")
    else:
        st.success("✅ Portafoglio bilanciato correttamente (100%).")

    # --- VISUALIZZAZIONE E ANALISI ---
    if total_current_weight > 0:
        tab1, tab2 = st.tabs(["📊 Distribuzione", "📈 Performance Storica"])
        
        with tab1:
            plot_data = pd.DataFrame([
                {'Nome': v['Nome'], 'Peso': v['Peso']} 
                for k, v in st.session_state.portfolio.items() if v['Peso'] > 0
            ])
            fig_pie = px.pie(plot_data, values='Peso', names='Nome', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(title="Composizione Target del Portafoglio")
            st.plotly_chart(fig_pie, use_container_width=True)

        with tab2:
            st.info("Clicca sul pulsante per scaricare i dati e calcolare l'andamento dell'ultimo anno.")
            if st.button("🚀 Genera Grafico di Performance"):
                with st.spinner('Scaricamento dati storici da Yahoo Finance...'):
                    # Scarico dati per 1 anno
                    raw_data = yf.download(tickers, period="1y", interval="1d")
                    
                    # Estrazione prezzi di chiusura
                    if len(tickers) > 1:
                        hist_data = raw_data['Close']
                    else:
                        hist_data = raw_data['Close'].to_frame()
                        hist_data.columns = tickers

                    # Pulizia dati
                    hist_data = hist_data.ffill().dropna()

                    if not hist_data.empty:
                        # Normalizzazione Base 100
                        # .iloc[0] potrebbe fallire se ci sono NaN all'inizio, bfill() aiuta
                        norm_data = hist_data.divide(hist_data.bfill().iloc[0]) * 100
                        
                        # Calcolo Portafoglio Pesato
                        portfolio_sim = pd.Series(0.0, index=norm_data.index)
                        for t in tickers:
                            weight = st.session_state.portfolio[t]['Peso'] / 100
                            portfolio_sim += norm_data[t] * weight
                        
                        # CREAZIONE GRAFICO
                        fig_line = go.Figure()
                        
                        # Linea Portfolio
                        fig_line.add_trace(go.Scatter(
                            x=portfolio_sim.index, y=portfolio_sim,
                            name="IL TUO PORTAFOGLIO",
                            line=dict(color='#2E7D32', width=4)
                        ))
                        
                        # Linee singoli Asset
                        for t in tickers:
                            fig_line.add_trace(go.Scatter(
                                x=norm_data.index, y=norm_data[t],
                                name=f"ETF: {t}",
                                line=dict(width=1, dash='dot'),
                                opacity=0.5
                            ))
                        
                        fig_line.update_layout(
                            title="Andamento Ipotetico Ultimi 12 Mesi (Base 100)",
                            xaxis_title="Data",
                            yaxis_title="Valore Normalizzato (100)",
                            hovermode="x unified",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        st.plotly_chart(fig_line, use_container_width=True)
                    else:
                        st.error("Dati non disponibili per il periodo selezionato.")

else:
    # Stato vuoto
    st.info("👈 Inizia aggiungendo un ETF dalla barra laterale (usa i ticker di Yahoo Finance).")
    col_intro1, col_intro2 = st.columns(2)
    with col_intro1:
        st.markdown("""
        ### Come iniziare:
        1. Inserisci un ticker (es. **SWDA.MI** per iShares MSCI World).
        2. Scegli la percentuale di allocazione.
        3. Imposta il tuo budget mensile.
        4. Visualizza come si sarebbe comportato il portafoglio nell'ultimo anno.
        """)
    with col_intro2:
        st.image("https://images.unsplash.com/photo-1611974717482-58a252ec074c?auto=format&fit=crop&q=80&w=1000")
