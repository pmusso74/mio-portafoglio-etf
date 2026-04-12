import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF Portfolio Manager", layout="wide", page_icon="📊")

# CSS per miglioramenti estetici
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

# --- SIDEBAR: SALVA & CARICA ---
st.sidebar.header("💾 Salva & Carica")

# 1. DOWNLOAD (Salvataggio)
if st.session_state.portfolio:
    # Trasformiamo il dizionario in DataFrame per l'esportazione
    save_data = []
    for t, d in st.session_state.portfolio.items():
        save_data.append({
            'Ticker': t,
            'Nome': d.get('Nome', ''),
            'Peso': d.get('Peso', 0),
            'Prezzo': d.get('Prezzo', 0.0),
            'Valuta': d.get('Valuta', 'EUR')
        })
    df_save = pd.DataFrame(save_data)
    csv = df_save.to_csv(index=False).encode('utf-8')
    
    st.sidebar.download_button(
        label="📥 Scarica Portafoglio (CSV)",
        data=csv,
        file_name="mio_portafoglio_etf.csv",
        mime="text/csv",
    )

# 2. UPLOAD (Caricamento)
uploaded_file = st.sidebar.file_uploader("Carica un file CSV salvato", type="csv")
if uploaded_file is not None:
    try:
        df_load = pd.read_csv(uploaded_file)
        new_portfolio = {}
        for _, row in df_load.iterrows():
            new_portfolio[row['Ticker']] = {
                'Nome': row['Nome'],
                'Peso': int(row['Peso']),
                'Prezzo': float(row['Prezzo']),
                'Valuta': row['Valuta']
            }
        st.session_state.portfolio = new_portfolio
        st.sidebar.success("✅ Portafoglio Caricato!")
        # Non facciamo rerun qui per evitare loop, lo stato si aggiornerà al prossimo widget
    except Exception as e:
        st.sidebar.error("Errore nel caricamento del file.")

st.sidebar.markdown("---")

# --- SIDEBAR: IMPOSTAZIONI INVESTIMENTO ---
st.sidebar.header("⚙️ Impostazioni Investimento")
total_monthly_investment = st.sidebar.number_input(
    "Investimento Mensile Totale (€)", min_value=0.0, value=1000.0, step=50.0
)
total_weekly_investment = total_monthly_investment / 4.33
st.sidebar.info(f"Settimanale: **{total_weekly_investment:,.2f} €**")

st.sidebar.markdown("---")
st.sidebar.subheader("➕ Aggiungi Asset")
new_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI)")
new_weight = st.sidebar.slider("Peso iniziale (%)", 0, 100, 10)

if st.sidebar.button("Aggiungi ETF"):
    if new_ticker:
        ticker_upper = new_ticker.upper().strip()
        try:
            with st.spinner(f'Ricerca {ticker_upper}...'):
                t_obj = yf.Ticker(ticker_upper)
                info = t_obj.info
                price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
                name = info.get('longName', ticker_upper)
                currency = info.get('currency', 'EUR')
                
                if price:
                    st.session_state.portfolio[ticker_upper] = {
                        'Nome': name, 'Peso': new_weight, 'Prezzo': price, 'Valuta': currency
                    }
                    st.rerun()
                else:
                    st.error("Dati non trovati.")
        except:
            st.error("Errore di connessione o ticker errato.")

# --- AREA PRINCIPALE: GESTIONE ---
if st.session_state.portfolio:
    st.subheader("📝 Il tuo Portafoglio")
    
    # Intestazioni
    cols = st.columns([2.5, 1.2, 1.2, 1.5, 1.5, 0.8])
    labels = ["**Nome ETF**", "**Prezzo**", "**Peso %**", "**Mensile**", "**Settimanale**", "**Azione**"]
    for col, label in zip(cols, labels): col.write(label)

    total_current_weight = 0
    tickers_list = list(st.session_state.portfolio.keys())

    for ticker in tickers_list:
        asset = st.session_state.portfolio[ticker]
        c1, c2, c3, c4, c5, c6 = st.columns([2.5, 1.2, 1.2, 1.5, 1.5, 0.8])
        
        c1.markdown(f"**{asset.get('Nome', ticker)}**<br><small>{ticker}</small>", unsafe_allow_html=True)
        c2.markdown(f"<span class='price-tag'>{asset.get('Prezzo',0):.2f} {asset.get('Valuta','EUR')}</span>", unsafe_allow_html=True)
        
        # Input Peso
        new_val = c3.number_input("%", 0, 100, int(asset.get('Peso', 0)), key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = new_val
        total_current_weight += new_val
        
        # Budget
        bm = (new_val / 100) * total_monthly_investment
        c4.write(f"**{bm:,.2f} €**")
        c5.write(f"{bm/4.33:,.2f} €")
        
        if c6.button("🗑️", key=f"del_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    # Validazione
    st.markdown("---")
    if total_current_weight > 100:
        st.error(f"⚠️ Totale: {total_current_weight}% - Supera il 100%!")
    elif total_current_weight < 100:
        st.warning(f"ℹ️ Totale: {total_current_weight}% - Hai ancora {100-total_current_weight}% libero.")
    else:
        st.success("✅ Portafoglio bilanciato correttamente.")

    # Grafici
    t1, t2 = st.tabs(["📊 Distribuzione", "📈 Performance 1Y"])
    with t1:
        plot_df = pd.DataFrame([{'N': v['Nome'], 'P': v['Peso']} for v in st.session_state.portfolio.values() if v['Peso'] > 0])
        if not plot_df.empty:
            st.plotly_chart(px.pie(plot_df, values='P', names='N', hole=0.4), use_container_width=True)
            
    with t2:
        if st.button("Carica Grafico Storico"):
            with st.spinner('Analisi in corso...'):
                data = yf.download(tickers_list, period="1y")['Close']
                if len(tickers_list) == 1: 
                    data = data.to_frame()
                    data.columns = tickers_list
                data = data.ffill().dropna()
                if not data.empty:
                    norm = data.divide(data.bfill().iloc[0]) * 100
                    port_sim = pd.Series(0.0, index=norm.index)
                    for t in tickers_list:
                        port_sim += norm[t] * (st.session_state.portfolio[t]['Peso'] / 100)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=port_sim.index, y=port_sim, name="PORTAFOGLIO", line=dict(color='gold', width=4)))
                    for t in tickers_list:
                        fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=t, line=dict(width=1), opacity=0.3))
                    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("👈 Inizia aggiungendo un ETF o caricando un file salvato.")
