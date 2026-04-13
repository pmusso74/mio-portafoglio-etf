import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="PAC ETF PRO", layout="wide", page_icon="💰")

# CSS per badge e stile
st.markdown("""
    <style>
    .isin-text { color: #666; font-size: 0.8rem; font-family: monospace; }
    .badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; color: white; }
    .acc { background-color: #1E88E5; }
    .dist { background-color: #FB8C00; }
    .ter-text { font-size: 0.85rem; color: #444; font-weight: 500; }
    .euro-value { color: #2e7d32; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI ---
@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency: return 1.0
    try:
        rate = yf.Ticker(f"{ticker_currency}EUR=X").info.get('regularMarketPrice') or \
               yf.Ticker(f"{ticker_currency}EUR=X").info.get('previousClose')
        return float(rate) if rate else 1.0
    except: return 1.0

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.header("💾 Persistenza Dati")

uploaded_file = st.sidebar.file_uploader("Carica file portafoglio", type="csv")
if uploaded_file is not None:
    try:
        df_load = pd.read_csv(uploaded_file)
        new_portfolio = {}
        for _, row in df_load.iterrows():
            t = str(row['Ticker'])
            new_portfolio[t] = {
                'Nome': row.get('Nome', t),
                'ISIN': row.get('ISIN', 'N/A'),
                'Politica': row.get('Politica', 'Acc'),
                'TER': row.get('TER', '0.00%'),
                'Peso': float(row.get('Peso', 0)),
                'Prezzo': float(row.get('Prezzo', 0)),
                'Valuta': row.get('Valuta', 'EUR'),
                'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_portfolio
        if 'Total_Budget' in df_load.columns:
            st.session_state.total_budget = float(df_load['Total_Budget'].iloc[0])
    except Exception as e:
        st.sidebar.error(f"Errore: {e}")

if st.session_state.portfolio:
    save_df = pd.DataFrame([
        {**{'Ticker': k, 'Total_Budget': st.session_state.total_budget}, **v} 
        for k, v in st.session_state.portfolio.items()
    ])
    st.sidebar.download_button("📥 Esporta CSV", save_df.to_csv(index=False).encode('utf-8'), "mio_pac_etf.csv")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configurazione")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget))

st.sidebar.subheader("➕ Aggiungi ETF")
new_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI)")
if st.sidebar.button("Cerca e Aggiungi"):
    if new_ticker:
        t_up = new_ticker.upper().strip()
        try:
            with st.spinner("Recupero dati da Yahoo Finance..."):
                t_obj = yf.Ticker(t_up)
                info = t_obj.info
                
                # Tentativo di recupero TER e ISIN (spesso vuoti per UCITS)
                raw_ter = info.get('annualReportExpenseRatio')
                ter_val = f"{raw_ter*100:.2f}%" if raw_ter else "0.20%" # Default se manca
                
                isin_val = info.get('isin', 'N/A')
                
                # Politica dividendi (euristica basata su dividendYield)
                yield_val = info.get('dividendYield', 0)
                policy = "Dist" if yield_val and yield_val > 0 else "Acc"
                
                st.session_state.portfolio[t_up] = {
                    'Nome': info.get('longName', t_up),
                    'ISIN': isin_val if isin_val != 'None' else 'N/A',
                    'Politica': policy,
                    'TER': ter_val,
                    'Peso': 0.0,
                    'Prezzo': float(info.get('currentPrice') or info.get('previousClose') or 0),
                    'Valuta': info.get('currency', 'EUR'),
                    'Cambio': get_exchange_rate(info.get('currency', 'EUR'))
                }
                st.rerun()
        except:
            st.sidebar.error("Ticker non trovato.")

# --- MAIN ---
st.title("💰 ETF PAC Planner")

if st.session_state.portfolio:
    # Intestazione Tabella Semplificata
    h_cols = st.columns([2.5, 1.2, 1.0, 1.0, 1.5, 1.5, 0.5])
    labels = ["ETF / ISIN", "Policy & TER", "Prezzo EUR", "Peso %", "Investimento", "Quote", ""]
    for col, lab in zip(h_cols, labels): col.write(f"**{lab}**")

    total_w = 0
    for ticker, asset in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2.5, 1.2, 1.0, 1.0, 1.5, 1.5, 0.5])
        
        # 1. NOME e ISIN
        with c1:
            st.markdown(f"**{asset['Nome'][:35]}**")
            new_isin = st.text_input("ISIN", asset['ISIN'], key=f"isin_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['ISIN'] = new_isin

        # 2. POLICY e TER
        with c2:
            pol = st.selectbox("Policy", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"pol_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['Politica'] = pol
            new_ter = st.text_input("TER", asset['TER'], key=f"ter_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['TER'] = new_ter

        # 3. PREZZO
        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        c3.markdown(f"**{p_eur:.2f} €**")

        # 4. PESO
        with c4:
            w = st.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['Peso'] = w
            total_w += w

        # 5. INVESTIMENTO
        inv = (w / 100) * st.session_state.total_budget
        c5.markdown(f"<span class='euro-value'>{inv:,.2f} €</span>", unsafe_allow_html=True)

        # 6. QUOTE
        q = inv / p_eur if p_eur > 0 else 0
        c6.write(f"{q:.2f}")

        # 7. DELETE
        if c7.button("🗑️", key=f"del_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    # Footer Validazione
    st.markdown("---")
    if total_w != 100:
        st.warning(f"Allocazione attuale: {total_w}% (deve essere 100%)")
    else:
        st.success("✅ Budget allocato correttamente.")

    # Riepilogo Visivo
    t1, t2 = st.tabs(["📊 Composizione", "ℹ️ Dettagli Tecnici"])
    with t1:
        df_fig = pd.DataFrame([{'ETF': t, 'Peso': a['Peso']} for t, a in st.session_state.portfolio.items() if a['Peso'] > 0])
        if not df_fig.empty:
            st.plotly_chart(px.pie(df_fig, values='Peso', names='ETF', hole=0.4))
    
    with t2:
        # Una tabella riassuntiva pulita con i dati tecnici
        tech_data = []
        for t, a in st.session_state.portfolio.items():
            tech_data.append({
                "Ticker": t, "ISIN": a['ISIN'], "Tipo": a['Politica'], "TER": a['TER'], "Valuta Orig.": a['Valuta']
            })
        st.table(tech_data)

else:
    st.info("👈 Inizia aggiungendo un ticker nella barra laterale (es: SWDA.MI, CSSPX.MI, EIMI.MI)")
