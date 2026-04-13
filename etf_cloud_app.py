import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner Pro", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv"

# --- CSS ESTETICA ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 1.0rem; line-height: 1.1; margin-bottom: 2px; }
    .isin-label { color: #d32f2f; font-weight: bold; font-family: monospace; font-size: 0.8rem; }
    .real-status { color: #444; font-size: 0.75rem; background: #e8f5e9; padding: 4px 8px; border-radius: 4px; border-left: 4px solid #2e7d32; margin-top: 5px; }
    .just-link-btn { 
        display: inline-block; margin-top: 5px; padding: 2px 10px; 
        background-color: #ffffff; color: #1a73e8 !important; 
        text-decoration: none !important; border: 1px solid #1a73e8;
        border-radius: 12px; font-size: 0.65rem; font-weight: 700; 
    }
    .just-link-btn:hover { background-color: #1a73e8; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---
@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if not ticker_currency or ticker_currency == "EUR": return 1.0
    try:
        pair = f"{ticker_currency}EUR=X"
        data = yf.download(pair, period="1d", progress=False)
        return float(data['Close'].iloc[-1])
    except: return 1.0

def update_all_prices():
    if not st.session_state.portfolio: return
    with st.spinner("Aggiornamento dati di mercato..."):
        for ticker in list(st.session_state.portfolio.keys()):
            try:
                y_obj = yf.Ticker(ticker)
                inf = y_obj.info
                price = inf.get('currentPrice') or inf.get('regularMarketPrice') or inf.get('previousClose')
                if price:
                    st.session_state.portfolio[ticker]['Prezzo'] = float(price)
                    st.session_state.portfolio[ticker]['PrevClose'] = float(inf.get('previousClose', price))
                    st.session_state.portfolio[ticker]['Cambio'] = get_exchange_rate(inf.get('currency', 'EUR'))
            except: continue
        st.toast("✅ Prezzi aggiornati!")

def load_from_df(df):
    new_port = {}
    for _, row in df.iterrows():
        t = str(row['Ticker']).upper()
        new_port[t] = {
            'Nome': row.get('Nome', t), 
            'ISIN': str(row.get('ISIN', '')),
            'Politica': str(row.get('Politica', 'Acc')), 
            'TER': str(row.get('TER', '0.20%')),
            'Peso': float(row.get('Peso', 0)), 
            'Prezzo': float(row.get('Prezzo', 0)),
            'PrevClose': float(row.get('PrevClose', 0)),
            'Valuta': str(row.get('Valuta', 'EUR')), 
            'Cambio': float(row.get('Cambio', 1.0)),
            'Investito_Reale': float(row.get('Investito_Reale', 0.0)),
            'Quote_Reali': float(row.get('Quote_Reali', 0.0))
        }
    st.session_state.portfolio = new_port
    if 'Total_Budget' in df.columns: st.session_state.total_budget = float(df['Total_Budget'].iloc[0])

def save_data_locally():
    if st.session_state.portfolio:
        data_to_save = []
        for k, v in st.session_state.portfolio.items():
            row = {'Ticker': k, 'Total_Budget': st.session_state.total_budget}
            row.update(v)
            data_to_save.append(row)
        pd.DataFrame(data_to_save).to_csv(DB_FILE, index=False)
        return True
    return False

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    if os.path.exists(DB_FILE):
        try: load_from_df(pd.read_csv(DB_FILE))
        except: pass
if 'total_budget' not in st.session_state: st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configurazione PAC")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget), step=50.0)

st.sidebar.markdown("---")
with st.sidebar.expander("🔍 Aggiungi ETF", expanded=True):
    input_id = st.text_input("Ticker (es. SWDA.MI)").strip().upper()
    if st.button("AGGIUNGI AL PIANO"):
        if input_id:
            with st.spinner("Ricerca..."):
                try:
                    y_obj = yf.Ticker(input_id)
                    inf = y_obj.info
                    # Tentativo di recupero ISIN (non sempre presente in yfinance)
                    fetched_isin = y_obj.isin if hasattr(y_obj, 'isin') and y_obj.isin != '-' else ""
                    
                    if 'symbol' in inf:
                        st.session_state.portfolio[inf['symbol']] = {
                            'Nome': inf.get('shortName') or inf.get('longName') or inf['symbol'],
                            'ISIN': fetched_isin,
                            'Politica': 'Acc', 'TER': '0.20%', 'Peso': 0.0,
                            'Prezzo': float(inf.get('currentPrice') or inf.get('regularMarketPrice')),
                            'PrevClose': float(inf.get('previousClose') or 0),
                            'Valuta': inf.get('currency', 'EUR'),
                            'Cambio': get_exchange_rate(inf.get('currency', 'EUR')),
                            'Investito_Reale': 0.0, 'Quote_Reali': 0.0
                        }
                    else: st.error("Ticker non trovato.")
                except: st.error("Errore nel recupero dati.")

st.sidebar.markdown("---")
c_s1, c_s2 = st.sidebar.columns(2)
if c_s1.button("💾 SALVA", use_container_width=True):
    if save_data_locally(): st.sidebar.success("Dati salvati!")
if c_s2.button("🔄 AGGIORNA", use_container_width=True):
    update_all_prices()
    st.rerun()

# --- INTERFACCIA PRINCIPALE ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("👈 Inizia aggiungendo un ETF dalla barra laterale (usa i ticker di Yahoo Finance, es: CSSX5.MI).")
else:
    # Intestazioni Tabella
    cols = st.columns([2.5, 1.2, 0.8, 0.8, 1, 1, 1.2])
    headers = ["Asset / ISIN", "Dati (Politica/ISIN)", "Prezzo €", "Peso %", "Target €", "Drift %", "Azioni"]
    for col, h in zip(cols, headers): col.write(f"**{h}**")

    current_total_value = 0
    
    # Primo ciclo per calcolare il valore totale del portafoglio (necessario per il Drift)
    for ticker, asset in st.session_state.portfolio.items():
        current_total_value += (asset['Quote_Reali'] * asset['Prezzo'] * asset['Cambio'])

    # Secondo ciclo per la visualizzazione
    for ticker, asset in list(st.session_state.portfolio.items()):
        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        target_eur = (asset['Peso'] / 100) * st.session_state.total_budget
        asset_val_reale = asset['Quote_Reali'] * p_eur
        
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2.5, 1.2, 0.8, 0.8, 1, 1, 1.2])
        
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:40]}</div><div class='isin-label'>{ticker}</div>", unsafe_allow_html=True)
            if asset['Quote_Reali'] > 0:
                st.markdown(f"<div class='real-status'>Posseduto: {asset_val_reale:,.2f}€</div>", unsafe_allow_html=True)
            st.markdown(f"<a href='https://www.justetf.com/it/find-etf.html?query={asset['ISIN']}' target='_blank' class='just-link-btn'>JustETF ↗</a>", unsafe_allow_html=True)

        with c2:
            asset['Politica'] = st.selectbox("P", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"pol_{ticker}", label_visibility="collapsed")
            # Campo ISIN editabile
            asset['ISIN'] = st.text_input("ISIN", asset['ISIN'], key=f"isin_val_{ticker}", label_visibility="collapsed", placeholder="Inserisci ISIN")

        c3.write(f"**{p_eur:,.2f}**")
        asset['Peso'] = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        
        c5.markdown(f"**{target_eur:,.2f} €**")
        
        with c6:
            if current_total_value > 0:
                peso_reale = (asset_val_reale / current_total_value) * 100
                drift = peso_reale - asset['Peso']
                color = "#d32f2f" if abs(drift) > 3 else "#2e7d32"
                st.markdown(f"<b style='color:{color}'>{drift:+.1f}%</b>", unsafe_allow_html=True)
            else: st.write("-")

        with c7:
            act = st.columns(3)
            if act[0].button("➕", key=f"add_{ticker}", help="Registra acquisto quota target"):
                asset['Investito_Reale'] += target_eur
                asset['Quote_Reali'] += (target_eur / p_eur) if p_eur > 0 else 0
                st.rerun()
            if act[1].button("🧹", key=f"clr_{ticker}", help="Resetta quote"):
                asset['Investito_Reale'] = 0.0; asset['Quote_Reali'] = 0.0
                st.rerun()
            if act[2].button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; st.rerun()

    # --- RIEPILOGO METRICHE ---
    st.markdown("---")
    total_invested = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Capitale Versato", f"{total_invested:,.2f} €")
    m2.metric("Valore Attuale", f"{current_total_value:,.2f} €")
    pnl = current_total_value - total_invested
    pnl_perc = (pnl / total_invested * 100) if total_invested > 0 else 0
    m3.metric("Profit/Loss Totale", f"{pnl:+,.2f} €", f"{pnl_perc:+.2f}%")
    m4.metric("Budget Mensile", f"{st.session_state.total_budget:,.2f} €")

    # --- GRAFICI ---
    g1, g2 = st.columns([2, 1])
    with g1:
        tickers = list(st.session_state.portfolio.keys())
        if tickers:
            try:
                hist_data = yf.download(tickers, period="1y", progress=False)['Close']
                if len(tickers) == 1:
                    hist_data = hist_data.to_frame(); hist_data.columns = tickers
                norm_data = hist_data.ffill().divide(hist_data.iloc[0]).multiply(100)
                fig_line = px.line(norm_data, title="Performance 1 Anno (Base 100)", labels={'value': 'Rendimento %', 'index': 'Data'})
                fig_line.update_layout(template="plotly_white", height=400, legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig_line, use_container_width=True)
            except: st.warning("Dati storici non disponibili.")

    with g2:
        if current_total_value > 0:
            df_pie = pd.DataFrame([{'Asset': a['Nome'], 'Valore': a['Quote_Reali'] * a['Prezzo'] * a['Cambio']} for a in st.session_state.portfolio.values() if a['Quote_Reali'] > 0])
            fig_pie = px.pie(df_pie, values='Valore', names='Asset', title="Allocazione Reale", hole=0.4)
            fig_pie.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

# --- FOOTER ---
st.markdown("---")
st.caption("Dati forniti da Yahoo Finance. L'ISIN può essere modificato manualmente se non trovato automaticamente.")
