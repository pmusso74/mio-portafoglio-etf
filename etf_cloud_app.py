import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAC ETF Planner", layout="wide", page_icon="💰")

# CSS per pulizia visiva
st.markdown("""
    <style>
    .stNumberInput div div input { font-weight: bold; }
    .euro-value { color: #2e7d32; font-weight: bold; font-size: 1.1rem; }
    .share-value { color: #1565c0; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---

@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    """Ottiene il tasso di cambio per convertire in EUR"""
    if ticker_currency == "EUR" or not ticker_currency:
        return 1.0
    try:
        rate_ticker = f"{ticker_currency}EUR=X"
        data = yf.Ticker(rate_ticker)
        price = data.info.get('regularMarketPrice') or data.info.get('previousClose') or data.info.get('currentPrice')
        return float(price) if price else 1.0
    except:
        return 1.0

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- SIDEBAR: IMPORT/EXPORT ---
st.sidebar.header("💾 Salva e Carica")

# Caricamento
uploaded_file = st.sidebar.file_uploader("Carica portafoglio (CSV)", type="csv")
if uploaded_file is not None:
    try:
        df_load = pd.read_csv(uploaded_file)
        new_portfolio = {}
        for _, row in df_load.iterrows():
            ticker = str(row['Ticker'])
            new_portfolio[ticker] = {
                'Nome': row.get('Nome', ticker),
                'Peso': float(row.get('Peso', 0)),
                'Prezzo': float(row.get('Prezzo', 0)),
                'Valuta': row.get('Valuta', 'EUR'),
                'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_portfolio
        if 'Total_Budget' in df_load.columns:
            st.session_state.total_budget = float(df_load['Total_Budget'].iloc[0])
        st.sidebar.success("✅ Caricato!")
    except Exception as e:
        st.sidebar.error(f"Errore: {e}")

# Download
if st.session_state.portfolio:
    save_data = []
    for t, d in st.session_state.portfolio.items():
        save_data.append({
            'Ticker': t, 'Nome': d['Nome'], 'Peso': d['Peso'], 
            'Prezzo': d['Prezzo'], 'Valuta': d['Valuta'], 'Cambio': d.get('Cambio', 1.0),
            'Total_Budget': st.session_state.total_budget
        })
    csv = pd.DataFrame(save_data).to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("📥 Scarica Portafoglio (CSV)", csv, "mio_pac.csv", "text/csv")

# --- SIDEBAR: IMPOSTAZIONI ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Impostazioni PAC")
st.session_state.total_budget = st.sidebar.number_input(
    "Budget Mensile Totale (€)", min_value=0.0, value=float(st.session_state.total_budget), step=50.0
)

st.sidebar.subheader("➕ Aggiungi ETF")
new_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI)")
if st.sidebar.button("Aggiungi alla lista"):
    if new_ticker:
        t_up = new_ticker.upper().strip()
        try:
            with st.spinner("Recupero dati..."):
                info = yf.Ticker(t_up).info
                curr = info.get('currency', 'EUR')
                price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
                st.session_state.portfolio[t_up] = {
                    'Nome': info.get('longName', t_up),
                    'Peso': 0.0,
                    'Prezzo': float(price),
                    'Valuta': curr,
                    'Cambio': get_exchange_rate(curr)
                }
                st.rerun()
        except:
            st.sidebar.error("Ticker non trovato.")

# --- AREA PRINCIPALE ---
st.title("💰 ETF PAC Planner")
st.write(f"Pianificazione investimento mensile basata su un budget di **{st.session_state.total_budget:,.2f} €**")

if st.session_state.portfolio:
    # Intestazioni tabella
    cols = st.columns([2.5, 1.2, 1.2, 1.5, 1.5, 0.5])
    labels = ["**ETF / Ticker**", "**Prezzo (EUR)**", "**Peso Budget %**", "**Investimento Mensile**", "**Quote Stimate**", ""]
    for col, label in zip(cols, labels): col.write(label)

    total_weight = 0
    
    for ticker, asset in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5, c6 = st.columns([2.5, 1.2, 1.2, 1.5, 1.5, 0.5])
        
        # Prezzo convertito
        price_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        
        # Colonna 1: Nome
        c1.markdown(f"**{ticker}**<br><small>{asset['Nome'][:30]}</small>", unsafe_allow_html=True)
        
        # Colonna 2: Prezzo
        c2.markdown(f"{price_eur:.2f} €<br><small style='color:gray'>{asset['Prezzo']:.2f} {asset['Valuta']}</small>", unsafe_allow_html=True)
        
        # Colonna 3: Peso (Input dell'utente)
        new_w = c3.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = new_w
        total_weight += new_w
        
        # Colonna 4: Soldi da investire
        monthly_amt = (new_w / 100) * st.session_state.total_budget
        c4.markdown(f"<span class='euro-value'>{monthly_amt:,.2f} €</span>", unsafe_allow_html=True)
        
        # Colonna 5: Quote stimate
        est_shares = monthly_amt / price_eur if price_eur > 0 else 0
        c5.markdown(f"<span class='share-value'>{est_shares:.2f} quote</span>", unsafe_allow_html=True)
        
        # Colonna 6: Elimina
        if c6.button("🗑️", key=f"del_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    # Validazione Pesi
    st.markdown("---")
    if total_weight > 100:
        st.error(f"⚠️ Attenzione: La somma dei pesi è **{total_weight}%**. Superi il budget del {total_weight-100}%!")
    elif total_weight < 100:
        st.info(f"ℹ️ Hai allocato il **{total_weight}%** del budget. Rimane il {100-total_weight}% libero.")
    else:
        st.success("✅ Budget allocato correttamente al 100%.")

    # Grafici
    t1, t2 = st.tabs(["📊 Distribuzione Budget", "📈 Andamento Storico Asset"])
    
    with t1:
        # Mostra solo asset con peso > 0
        df_pie = pd.DataFrame([{'Ticker': t, 'Peso': a['Peso']} for t, a in st.session_state.portfolio.items() if a['Peso'] > 0])
        if not df_pie.empty:
            fig = px.pie(df_pie, values='Peso', names='Ticker', hole=0.4, title="Ripartizione del tuo investimento mensile")
            st.plotly_chart(fig, use_container_width=True)

    with t2:
        if st.button("Carica Grafico Storico (1 Anno)"):
            tickers = list(st.session_state.portfolio.keys())
            with st.spinner("Scaricamento dati..."):
                data = yf.download(tickers, period="1y")['Close'].ffill().dropna()
                if not data.empty:
                    if len(tickers) == 1: 
                        data = data.to_frame()
                        data.columns = tickers
                    # Normalizzazione
                    norm = data.divide(data.iloc[0]) * 100
                    fig_line = px.line(norm, title="Performance relativa degli ETF selezionati (Base 100)")
                    st.plotly_chart(fig_line, use_container_width=True)

else:
    st.info("👈 Inizia impostando un budget e aggiungendo i ticker degli ETF nella barra laterale.")
