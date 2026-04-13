import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF Pro Portfolio Manager", layout="wide", page_icon="📈")

# CSS per rifiniture
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .buy-signal { color: #2e7d32; font-weight: bold; }
    .price-sub { font-size: 0.8rem; color: #666; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---

@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    """Recupera il tasso di cambio verso EUR"""
    if ticker_currency == "EUR":
        return 1.0
    try:
        # Esempio: USDEUR=X
        rate_ticker = f"{ticker_currency}EUR=X"
        data = yf.Ticker(rate_ticker)
        return data.info.get('regularMarketPrice') or data.info.get('previousClose') or 1.0
    except:
        return 1.0

def update_all_prices():
    """Aggiorna i prezzi e i tassi di cambio per tutto il portafoglio"""
    if not st.session_state.portfolio:
        return
    
    with st.spinner("Aggiornamento prezzi in corso..."):
        for ticker in st.session_state.portfolio:
            t_obj = yf.Ticker(ticker)
            info = t_obj.info
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            if price:
                st.session_state.portfolio[ticker]['Prezzo'] = price
                # Aggiorna anche il cambio
                currency = st.session_state.portfolio[ticker]['Valuta']
                st.session_state.portfolio[ticker]['Cambio'] = get_exchange_rate(currency)
        st.toast("✅ Prezzi aggiornati!")

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'monthly_investment' not in st.session_state:
    st.session_state.monthly_investment = 1000.0

# --- SIDEBAR: GESTIONE ---
st.sidebar.header("📂 Gestione Portafoglio")

# UPLOAD
uploaded_file = st.sidebar.file_uploader("Carica CSV", type="csv")
if uploaded_file is not None:
    try:
        df_load = pd.read_csv(uploaded_file)
        new_portfolio = {}
        for _, row in df_load.iterrows():
            new_portfolio[row['Ticker']] = {
                'Nome': row['Nome'],
                'Peso': float(row['Peso']),
                'Prezzo': float(row['Prezzo']),
                'Valuta': row.get('Valuta', 'EUR'),
                'Quote': float(row.get('Quote', 0.0)),
                'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_portfolio
        if 'Monthly_Inv' in df_load.columns:
            st.session_state.monthly_investment = float(df_load['Monthly_Inv'].iloc[0])
        st.sidebar.success("Portafoglio caricato!")
    except Exception as e:
        st.sidebar.error(f"Errore nel caricamento: {e}")

# SETTINGS INVESTIMENTO
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Impostazioni PAC")
st.session_state.monthly_investment = st.sidebar.number_input(
    "Budget Mensile (€)", min_value=0.0, value=st.session_state.monthly_investment, step=50.0
)

# DOWNLOAD
if st.session_state.portfolio:
    save_data = []
    for t, d in st.session_state.portfolio.items():
        save_data.append({
            'Ticker': t, 'Nome': d['Nome'], 'Peso': d['Peso'], 
            'Prezzo': d['Prezzo'], 'Valuta': d['Valuta'], 
            'Quote': d['Quote'], 'Cambio': d.get('Cambio', 1.0),
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
            info = yf.Ticker(t_up).info
            curr = info.get('currency', 'EUR')
            st.session_state.portfolio[t_up] = {
                'Nome': info.get('longName', t_up),
                'Peso': 0.0,
                'Prezzo': info.get('currentPrice') or info.get('previousClose'),
                'Valuta': curr,
                'Quote': 0.0,
                'Cambio': get_exchange_rate(curr)
            }
            st.rerun()
        except:
            st.sidebar.error("Ticker non trovato.")

# --- DASHBOARD PRINCIPALE ---
st.title("📊 ETF Pro Portfolio Manager")

if st.session_state.portfolio:
    # Calcolo Valore Totale Attuale
    total_value_eur = 0
    for t, a in st.session_state.portfolio.items():
        total_value_eur += (a['Quote'] * a['Prezzo'] * a.get('Cambio', 1.0))
    
    next_investment_total = total_value_eur + st.session_state.monthly_investment

    # Metriche principali
    m1, m2, m3 = st.columns(3)
    m1.metric("Valore Attuale Portafoglio", f"{total_value_eur:,.2f} €")
    m2.metric("Budget da Investire", f"{st.session_state.monthly_investment:,.2f} €")
    m3.metric("Nuovo Totale Previsto", f"{next_investment_total:,.2f} €")

    st.markdown("### 📝 Analisi e Rebalancing")
    
    # Intestazioni Tabella
    cols = st.columns([2, 1, 1, 1, 1, 1, 1.2, 0.5])
    fields = ["ETF", "Prezzo (EUR)", "Quote Attuali", "Valore (€)", "Peso Target %", "Target (€)", "ORDINE PAC", ""]
    for col, f in zip(cols, fields): col.write(f"**{f}**")

    total_target_weight = 0
    
    for ticker, asset in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2, 1, 1, 1, 1, 1, 1.2, 0.5])
        
        # 1. Info e Conversione Prezzo
        price_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        curr_val = asset['Quote'] * price_eur
        
        c1.markdown(f"**{ticker}**<br><small>{asset['Nome'][:25]}</small>", unsafe_allow_html=True)
        c2.markdown(f"{price_eur:.2f} €<br><span class='price-sub'>{asset['Prezzo']:.2f} {asset['Valuta']}</span>", unsafe_allow_html=True)
        
        # 2. Input Quote e Peso
        new_shares = c3.number_input("Quote", min_value=0.0, value=float(asset['Quote']), key=f"q_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Quote'] = new_shares
        
        c4.write(f"{curr_val:,.2f} €")
        
        new_w = c5.number_input("Weight %", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = new_w
        total_target_weight += new_w
        
        # 3. Calcolo Rebalancing (L'obiettivo è portare l'asset al % del valore totale post-investimento)
        target_val_eur = (new_w / 100) * next_investment_total
        c6.write(f"{target_val_eur:,.2f} €")
        
        # Quanto comprare oggi?
        to_buy_eur = target_val_eur - curr_val
        to_buy_shares = to_buy_eur / price_eur if price_eur > 0 else 0
        
        if to_buy_eur > 0:
            c7.markdown(f"<span class='buy-signal'>COMPRA: {to_buy_eur:,.2f}€</span><br>({to_buy_shares:.2f} quote)", unsafe_allow_html=True)
        else:
            c7.markdown(f"<span style='color:orange'>Mantieni</span><br><small>Sopra target di {abs(to_buy_eur):.2f}€</small>", unsafe_allow_html=True)

        if c8.button("🗑️", key=f"del_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    # Alert Pesi
    if total_target_weight != 100:
        st.warning(f"⚠️ La somma dei pesi target è {total_target_weight}%. Per un rebalancing corretto dovrebbe essere 100%.")

    # --- GRAFICI ---
    t1, t2 = st.tabs(["📊 Composizione Portafoglio", "📈 Analisi Storica (Normalizzata)"])
    
    with t1:
        fig_data = []
        for t, a in st.session_state.portfolio.items():
            if a['Quote'] > 0:
                fig_data.append({'Ticker': t, 'Valore': a['Quote'] * a['Prezzo'] * a.get('Cambio', 1.0)})
        
        if fig_data:
            df_pie = pd.DataFrame(fig_data)
            fig = px.pie(df_pie, values='Valore', names='Ticker', hole=0.5, title="Distribuzione Attuale in EUR")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aggiungi quote per vedere la distribuzione.")

    with t2:
        if st.button("Genera Grafico Storico 1 Anno"):
            tickers = list(st.session_state.portfolio.keys())
            if tickers:
                with st.spinner("Scaricamento dati storici..."):
                    try:
                        # Download dati
                        hist_data = yf.download(tickers, period="1y")['Close']
                        if len(tickers) == 1:
                            hist_data = hist_data.to_frame()
                            hist_data.columns = tickers
                        
                        hist_data = hist_data.ffill().dropna()
                        
                        # Normalizzazione a 100
                        norm_data = hist_data.divide(hist_data.iloc[0]) * 100
                        
                        # Calcolo Portafoglio Teorico (basato sui pesi target)
                        portfolio_sim = pd.Series(0.0, index=norm_data.index)
                        for t in tickers:
                            weight = st.session_state.portfolio[t]['Peso'] / 100
                            portfolio_sim += norm_data[t] * weight
                        
                        fig_hist = go.Figure()
                        fig_hist.add_trace(go.Scatter(x=portfolio_sim.index, y=portfolio_sim, name="IL TUO PORTAFOGLIO (Target)", line=dict(color='gold', width=4)))
                        
                        for t in tickers:
                            fig_hist.add_trace(go.Scatter(x=norm_data.index, y=norm_data[t], name=t, line=dict(width=1), opacity=0.4))
                        
                        fig_hist.update_layout(title="Performance Relativa 1 Anno (Base 100)", ylabel="Valore Normalizzato")
                        st.plotly_chart(fig_hist, use_container_width=True)
                    except Exception as e:
                        st.error(f"Errore nel recupero dati: {e}")

else:
    st.info("👈 Inizia configurando il tuo budget mensile e aggiungendo i ticker degli ETF nella barra laterale.")
