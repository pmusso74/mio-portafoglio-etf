import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAC ETF Planner PRO", layout="wide", page_icon="💰")

# CSS per migliorare la leggibilità
st.markdown("""
    <style>
    .isin-label { color: #666; font-size: 0.8rem; }
    .euro-amount { color: #2e7d32; font-weight: bold; font-size: 1.1rem; }
    .share-count { color: #1565c0; font-weight: 500; }
    .stTextInput input { font-size: 0.85rem; height: 30px; }
    .stSelectbox div div div { font-size: 0.85rem; height: 30px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---
@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency: return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose') or t.info.get('currentPrice')
        return float(rate) if rate else 1.0
    except: return 1.0

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- SIDEBAR: GESTIONE FILE ---
st.sidebar.header("💾 Persistenza Dati")

uploaded_file = st.sidebar.file_uploader("Carica Portafoglio (CSV)", type="csv")
if uploaded_file is not None:
    try:
        df_load = pd.read_csv(uploaded_file)
        new_portfolio = {}
        for _, row in df_load.iterrows():
            ticker = str(row['Ticker'])
            new_portfolio[ticker] = {
                'Nome': row.get('Nome', ticker),
                'ISIN': str(row.get('ISIN', 'N/A')),
                'Politica': str(row.get('Politica', 'Acc')),
                'TER': str(row.get('TER', '0.00%')),
                'Peso': float(row.get('Peso', 0.0)),
                'Prezzo': float(row.get('Prezzo', 0.0)),
                'Valuta': row.get('Valuta', 'EUR'),
                'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_portfolio
        if 'Total_Budget' in df_load.columns:
            st.session_state.total_budget = float(df_load['Total_Budget'].iloc[0])
        st.sidebar.success("✅ Caricato con successo!")
    except Exception as e:
        st.sidebar.error(f"Errore caricamento: {e}")

# Download Portafoglio
if st.session_state.portfolio:
    save_data = []
    for t, a in st.session_state.portfolio.items():
        # Creiamo un dizionario piatto per il CSV
        item = {'Ticker': t, 'Total_Budget': st.session_state.total_budget}
        item.update(a)
        save_data.append(item)
    df_save = pd.DataFrame(save_data)
    st.sidebar.download_button("📥 Scarica Portafoglio (CSV)", df_save.to_csv(index=False).encode('utf-8'), "mio_piano_pac.csv", "text/csv")

# --- SIDEBAR: SETTINGS ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Impostazioni PAC")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget), step=50.0)

st.sidebar.subheader("➕ Aggiungi ETF")
new_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI)")
if st.sidebar.button("Aggiungi Asset"):
    if new_ticker:
        t_up = new_ticker.upper().strip()
        try:
            with st.spinner(f"Ricerca {t_up}..."):
                info = yf.Ticker(t_up).info
                curr = info.get('currency', 'EUR')
                price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
                st.session_state.portfolio[t_up] = {
                    'Nome': info.get('longName', t_up),
                    'ISIN': info.get('isin', 'N/A'),
                    'Politica': 'Acc' if not info.get('dividendYield') else 'Dist',
                    'TER': '0.20%', # Valore di esempio editabile
                    'Peso': 0.0,
                    'Prezzo': float(price),
                    'Valuta': curr,
                    'Cambio': get_exchange_rate(curr)
                }
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Errore: {e}")

# --- AREA PRINCIPALE ---
st.title("💰 ETF PAC Planner")
st.write(f"Distribuzione del budget mensile: **{st.session_state.total_budget:,.2f} €**")

if st.session_state.portfolio:
    # Intestazione Colonne
    h1, h2, h3, h4, h5, h6, h7 = st.columns([2.2, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
    labels = ["ETF / ISIN", "Policy / TER", "Prezzo (EUR)", "Peso %", "Investimento", "Quote", ""]
    for col, lab in zip([h1, h2, h3, h4, h5, h6, h7], labels): col.markdown(f"**{lab}**")

    total_weight = 0
    
    # Loop sugli asset
    for ticker, asset in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2.2, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
        
        # 1. Nome e ISIN
        with c1:
            st.markdown(f"**{asset.get('Nome', ticker)[:30]}**")
            new_isin = st.text_input("ISIN", asset.get('ISIN', 'N/A'), key=f"isin_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['ISIN'] = new_isin
        
        # 2. Policy e TER
        with c2:
            pol_options = ["Acc", "Dist"]
            current_pol = asset.get('Politica', 'Acc')
            pol_idx = pol_options.index(current_pol) if current_pol in pol_options else 0
            new_pol = st.selectbox("Policy", pol_options, index=pol_idx, key=f"pol_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['Politica'] = new_pol
            
            new_ter = st.text_input("TER", asset.get('TER', '0.20%'), key=f"ter_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['TER'] = new_ter
            
        # 3. Prezzo Convertito
        price_eur = float(asset.get('Prezzo', 0)) * float(asset.get('Cambio', 1.0))
        c3.markdown(f"**{price_eur:.2f} €**")
        
        # 4. Peso %
        with c4:
            w = st.number_input("%", 0, 100, int(asset.get('Peso', 0)), key=f"w_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['Peso'] = w
            total_weight += w
            
        # 5. Investimento in Euro
        investment_eur = (w / 100) * st.session_state.total_budget
        c5.markdown(f"<span class='euro-amount'>{investment_eur:,.2f} €</span>", unsafe_allow_html=True)
        
        # 6. Quote Stimate
        shares = investment_eur / price_eur if price_eur > 0 else 0
        c6.markdown(f"<span class='share-count'>{shares:.2f} quote</span>", unsafe_allow_html=True)
        
        # 7. Elimina
        if c7.button("🗑️", key=f"del_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    # --- FOOTER & VALIDAZIONE ---
    st.markdown("---")
    if total_weight > 100:
        st.error(f"⚠️ Somma pesi: {total_weight}% (Superi il budget del {total_weight-100}%)")
    elif total_weight < 100:
        st.warning(f"ℹ️ Somma pesi: {total_weight}% (Hai ancora il {100-total_weight}% da allocare)")
    else:
        st.success("✅ Budget allocato correttamente (100%)")

    # Grafico di distribuzione
    df_plot = pd.DataFrame([{'ETF': t, 'Peso': a['Peso']} for t, a in st.session_state.portfolio.items() if a['Peso'] > 0])
    if not df_plot.empty:
        st.plotly_chart(px.pie(df_plot, values='Peso', names='ETF', hole=0.4, title="Distribuzione del Budget"), use_container_width=True)

else:
    st.info("👈 Inizia aggiungendo un ETF dalla barra laterale o caricando un file CSV salvato.")
