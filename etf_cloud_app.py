import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF Portfolio Manager", layout="wide", page_icon="📊")

# CSS per migliorare la leggibilità delle tabelle
st.markdown("""
    <style>
    .stNumberInput div div input { font-weight: bold; }
    .price-tag { color: #1E88E5; font-weight: bold; }
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

# Calcolo settimanale medio (4.33 settimane in un mese)
total_weekly_investment = total_monthly_investment / 4.33

st.sidebar.info(f"Equivale a circa: **{total_weekly_investment:,.2f} € / settimana**")

st.sidebar.markdown("---")
st.sidebar.subheader("➕ Aggiungi Asset")
new_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI, CSSX5E.MI)")
new_weight = st.sidebar.slider("Allocazione iniziale (%)", 0, 100, 10)

if st.sidebar.button("Aggiungi al Portafoglio"):
    if new_ticker:
        ticker_upper = new_ticker.upper().strip()
        if ticker_upper not in st.session_state.portfolio:
            try:
                with st.spinner(f'Ricerca di {ticker_upper}...'):
                    t_obj = yf.Ticker(ticker_upper)
                    info = t_obj.info
                    # Cerchiamo il prezzo corrente (gestisce diversi mercati)
                    price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
                    name = info.get('longName', ticker_upper)
                    currency = info.get('currency', 'EUR')
                    
                    if price:
                        st.session_state.portfolio[ticker_upper] = {
                            'Nome': name,
                            'Peso': new_weight,
                            'Prezzo': price,
                            'Valuta': currency
                        }
                        st.success(f"Aggiunto: {name}")
                    else:
                        st.error("Impossibile recuperare il prezzo. Controlla il ticker.")
            except Exception as e:
                st.error(f"Errore: Ticker non trovato.")
        else:
            st.warning("L'asset è già presente.")

# --- AREA PRINCIPALE: GESTIONE PORTAFOGLIO ---
if st.session_state.portfolio:
    st.subheader("📝 Gestione Asset e Budget")
    
    # Intestazioni Tabella (6 colonne)
    cols_header = st.columns([2.5, 1.2, 1.2, 1.5, 1.5, 0.8])
    cols_header[0].write("**Nome ETF**")
    cols_header[1].write("**Prezzo**")
    cols_header[2].write("**Peso %**")
    cols_header[3].write("**Mensile**")
    cols_header[4].write("**Settimanale**")
    cols_header[5].write("**Azione**")

    total_current_weight = 0
    
    for ticker in list(st.session_state.portfolio.keys()):
        asset = st.session_state.portfolio[ticker]
        c1, c2, c3, c4, c5, c6 = st.columns([2.5, 1.2, 1.2, 1.5, 1.5, 0.8])
        
        # 1. Nome e Ticker
        c1.markdown(f"**{asset['Nome']}**<br><small>{ticker}</small>", unsafe_allow_html=True)
        
        # 2. Prezzo (con valuta)
        c2.markdown(f"<span class='price-tag'>{asset['Prezzo']:.2f} {asset['Valuta']}</span>", unsafe_allow_html=True)
        
        # 3. Input Peso %
        new_val = c3.number_input(f"%", min_value=0, max_value=100, 
                                 value=int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = new_val
        total_current_weight += new_val
        
        # 4. Calcolo Budget Mensile
        budget_m = (new_val / 100) * total_monthly_investment
        c4.write(f"**{budget_m:,.2f} €**")
        
        # 5. Calcolo Budget Settimanale
        budget_w = budget_m / 4.33
        c5.write(f"{budget_w:,.2f} €")
        
        # 6. Elimina
        if c6.button("🗑️", key=f"del_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    # --- VALIDAZIONE ---
    st.markdown("---")
    col_v1, col_v2 = st.columns(2)
    if total_current_weight > 100:
        col_v1.error(f"⚠️ Totale: {total_current_weight}% (Supera il 100%)")
    elif total_current_weight < 100:
        col_v1.warning(f"ℹ️ Totale: {total_current_weight}% (Manca il {100-total_current_weight}%)")
    else:
        col_v1.success("✅ Portafoglio bilanciato (100%)")

    # --- GRAFICI ---
    if total_current_weight > 0:
        t1, t2 = st.tabs(["📊 Distribuzione Peso", "📈 Simulazione Performance"])
        
        with t1:
            plot_data = pd.DataFrame([
                {'Nome': v['Nome'], 'Peso': v['Peso']} 
                for k, v in st.session_state.portfolio.items() if v['Peso'] > 0
            ])
            fig_pie = px.pie(plot_data, values='Peso', names='Nome', hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_pie, use_container_width=True)

        with t2:
            if st.button("Genera Grafico Storico (1 Anno)"):
                with st.spinner('Scaricamento dati...'):
                    tickers = list(st.session_state.portfolio.keys())
                    data = yf.download(tickers, period="1y")['Close']
                    
                    if len(tickers) == 1:
                        data = data.to_frame()
                        data.columns = tickers

                    data = data.ffill().dropna()
                    if not data.empty:
                        # Normalizzazione base 100
                        norm = data.divide(data.iloc[0]) * 100
                        
                        # Portafoglio pesato
                        portfolio_val = pd.Series(0.0, index=norm.index)
                        for t in tickers:
                            weight = st.session_state.portfolio[t]['Peso'] / 100
                            portfolio_val += norm[t] * weight
                        
                        fig_line = go.Figure()
                        fig_line.add_trace(go.Scatter(x=portfolio_val.index, y=portfolio_val, 
                                                     name="PORTAFOGLIO", line=dict(color='gold', width=4)))
                        for t in tickers:
                            fig_line.add_trace(go.Scatter(x=norm.index, y=norm[t], name=t, 
                                                         line=dict(width=1), opacity=0.4))
                        
                        fig_line.update_layout(title="Andamento Ipotetico (Base 100)", hovermode="x unified")
                        st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("👈 Inizia aggiungendo un ETF dalla barra laterale per vedere i calcoli di investimento.")
    st.image("https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?auto=format&fit=crop&q=80&w=1000", width=700)
