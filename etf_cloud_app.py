import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF Pro Portfolio Manager", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .buy-signal { color: #2e7d32; font-weight: bold; }
    .price-sub { font-size: 0.8rem; color: #666; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---

@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency:
        return 1.0
    try:
        rate_ticker = f"{ticker_currency}EUR=X"
        data = yf.Ticker(rate_ticker)
        # Cerchiamo di ottenere un prezzo valido
        price = data.info.get('regularMarketPrice') or data.info.get('previousClose') or data.info.get('currentPrice')
        return float(price) if price else 1.0
    except:
        return 1.0

def update_all_prices():
    if not st.session_state.portfolio:
        return
    with st.spinner("Aggiornamento prezzi in corso..."):
        for ticker in st.session_state.portfolio:
            try:
                t_obj = yf.Ticker(ticker)
                info = t_obj.info
                price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
                if price:
                    st.session_state.portfolio[ticker]['Prezzo'] = float(price)
                    curr = info.get('currency', 'EUR')
                    st.session_state.portfolio[ticker]['Cambio'] = get_exchange_rate(curr)
            except:
                continue
        st.toast("✅ Prezzi aggiornati!")

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'monthly_investment' not in st.session_state:
    st.session_state.monthly_investment = 1000.0

# --- SIDEBAR ---
st.sidebar.header("📂 Gestione Portafoglio")

# UPLOAD (Migliorato con gestione errori colonne mancanti)
uploaded_file = st.sidebar.file_uploader("Carica CSV", type="csv")
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
                'Quote': float(row.get('Quote', 0.0)),
                'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_portfolio
        if 'Monthly_Inv' in df_load.columns:
            st.session_state.monthly_investment = float(df_load['Monthly_Inv'].iloc[0])
        st.sidebar.success("Portafoglio caricato!")
    except Exception as e:
        st.sidebar.error(f"Errore caricamento: {e}")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Impostazioni PAC")
st.session_state.monthly_investment = st.sidebar.number_input(
    "Budget Mensile (€)", min_value=0.0, value=float(st.session_state.monthly_investment), step=50.0
)

# DOWNLOAD (Corretto per evitare KeyError)
if st.session_state.portfolio:
    save_data = []
    for t, d in st.session_state.portfolio.items():
        save_data.append({
            'Ticker': t, 
            'Nome': d.get('Nome', t), 
            'Peso': d.get('Peso', 0), 
            'Prezzo': d.get('Prezzo', 0), 
            'Valuta': d.get('Valuta', 'EUR'), 
            'Quote': d.get('Quote', 0.0), 
            'Cambio': d.get('Cambio', 1.0),
            'Monthly_Inv': st.session_state.monthly_investment
        })
    csv = pd.DataFrame(save_data).to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("📥 Scarica Portafoglio (CSV)", csv, "portfolio_etf.csv", "text/csv")

if st.sidebar.button("🔄 Aggiorna Prezzi Ora"):
    update_all_prices()
    st.rerun()

# AGGIUNTA ASSET
st.sidebar.markdown("---")
st.sidebar.subheader("➕ Aggiungi ETF")
new_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI)")
if st.sidebar.button("Aggiungi"):
    if new_ticker:
        t_up = new_ticker.upper().strip()
        try:
            with st.spinner("Recupero dati..."):
                info = yf.Ticker(t_up).info
                curr = info.get('currency', 'EUR')
                price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
                st.session_state.portfolio[t_up] = {
                    'Nome': info.get('longName', t_up),
                    'Peso': 0.0,
                    'Prezzo': float(price),
                    'Valuta': curr,
                    'Quote': 0.0,
                    'Cambio': get_exchange_rate(curr)
                }
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Ticker non trovato: {e}")

# --- DASHBOARD PRINCIPALE ---
st.title("📊 ETF Pro Portfolio Manager")

if st.session_state.portfolio:
    # Calcolo Valore Totale
    total_value_eur = sum(float(a.get('Quote', 0)) * float(a.get('Prezzo', 0)) * float(a.get('Cambio', 1.0)) 
                          for a in st.session_state.portfolio.values())
    
    next_investment_total = total_value_eur + st.session_state.monthly_investment

    m1, m2, m3 = st.columns(3)
    m1.metric("Valore Attuale", f"{total_value_eur:,.2f} €")
    m2.metric("Budget PAC", f"{st.session_state.monthly_investment:,.2f} €")
    m3.metric("Obiettivo Post-Investimento", f"{next_investment_total:,.2f} €")

    st.markdown("### 📝 Analisi e Rebalancing")
    
    cols = st.columns([2, 1, 1, 1, 1, 1, 1.2, 0.5])
    labels = ["ETF", "Prezzo (EUR)", "Quote Possedute", "Valore Attuale", "Target %", "Target (€)", "AZIONE PAC", ""]
    for col, f in zip(cols, labels): col.write(f"**{f}**")

    total_target_weight = 0
    
    for ticker, asset in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2, 1, 1, 1, 1, 1, 1.2, 0.5])
        
        price_eur = float(asset.get('Prezzo', 0)) * float(asset.get('Cambio', 1.0))
        curr_val = float(asset.get('Quote', 0)) * price_eur
        
        c1.markdown(f"**{ticker}**<br><small>{asset.get('Nome', '')[:25]}</small>", unsafe_allow_html=True)
        c2.markdown(f"{price_eur:.2f} €<br><span class='price-sub'>{asset.get('Prezzo',0):.2f} {asset.get('Valuta','EUR')}</span>", unsafe_allow_html=True)
        
        # Input Quote e Peso (Usiamo get per sicurezza)
        q_val = float(asset.get('Quote', 0.0))
        new_shares = c3.number_input("Quote", min_value=0.0, value=q_val, key=f"q_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Quote'] = new_shares
        
        c4.write(f"{curr_val:,.2f} €")
        
        w_val = int(asset.get('Peso', 0))
        new_w = c5.number_input("%", 0, 100, w_val, key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = new_w
        total_target_weight += new_w
        
        target_val_eur = (new_w / 100) * next_investment_total
        c6.write(f"{target_val_eur:,.2f} €")
        
        to_buy_eur = target_val_eur - curr_val
        if to_buy_eur > 0:
            shares_to_buy = to_buy_eur / price_eur if price_eur > 0 else 0
            c7.markdown(f"<span class='buy-signal'>COMPRA {to_buy_eur:,.2f}€</span><br><small>≈ {shares_to_buy:.2f} quote</small>", unsafe_allow_html=True)
        else:
            c7.markdown("<span style='color:orange'>MANTIENI</span>", unsafe_allow_html=True)

        if c8.button("🗑️", key=f"del_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    if total_target_weight != 100:
        st.warning(f"⚠️ Somma pesi: {total_target_weight}% (deve essere 100%)")

    # --- GRAFICI ---
    t1, t2 = st.tabs(["📊 Composizione", "📈 Performance Storica"])
    with t1:
        fig_data = [{'T': t, 'V': a['Quote']*a['Prezzo']*a.get('Cambio', 1.0)} for t, a in st.session_state.portfolio.items() if a.get('Quote', 0) > 0]
        if fig_data:
            st.plotly_chart(px.pie(pd.DataFrame(fig_data), values='V', names='T', hole=0.4), use_container_width=True)
    with t2:
        if st.button("Carica Grafico Storico"):
            tickers = list(st.session_state.portfolio.keys())
            if tickers:
                data = yf.download(tickers, period="1y")['Close'].ffill().dropna()
                if not data.empty:
                    if len(tickers) == 1: data = data.to_frame(); data.columns = tickers
                    norm = data.divide(data.iloc[0]) * 100
                    fig = go.Figure()
                    for t in tickers:
                        fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=t, opacity=0.5))
                    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("👈 Aggiungi un ETF per iniziare.")
