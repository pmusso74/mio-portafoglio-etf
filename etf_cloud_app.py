import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import urllib.parse
import re

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner", layout="wide", page_icon="💰")

# CSS per pulizia e stile
st.markdown("""
    <style>
    .etf-container { margin-bottom: 10px; }
    .etf-name { color: #1E88E5; font-weight: bold; font-size: 1.1rem; line-height: 1.2; }
    .etf-meta { color: #555; font-size: 0.9rem; margin-top: 2px; }
    .isin-code { color: #888; font-size: 0.85rem; font-family: monospace; font-weight: bold; }
    .just-link { 
        display: inline-block; 
        margin-top: 6px;
        padding: 5px 12px; 
        background-color: #FB8C00; 
        color: white !important; 
        text-decoration: none !important; 
        border-radius: 4px; 
        font-size: 0.75rem; 
        font-weight: bold;
        text-transform: uppercase;
    }
    .just-link:hover { background-color: #EF6C00; }
    .euro-value { color: #2e7d32; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI PULIZIA ---
def get_clean_isin(val):
    """Restituisce l'ISIN solo se è un codice valido di 12 caratteri, altrimenti stringa vuota."""
    s = str(val).strip().upper()
    # Rimuove sporcizia comune
    if s in ["N/A", "N/", "NONE", "NAN", "NULL", ""] or len(s) < 10:
        return ""
    # Verifica che assomigli a un ISIN (2 lettere + 10 numeri/lettere)
    if re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", s):
        return s
    return ""

@st.cache_data(ttl=3600)
def get_exchange_rate(ticker_currency):
    if ticker_currency == "EUR" or not ticker_currency: return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose') or t.info.get('currentPrice')
        return float(rate) if rate else 1.0
    except: return 1.0

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state: st.session_state.portfolio = {}
if 'total_budget' not in st.session_state: st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.header("💾 Archivio Portafoglio")
uploaded_file = st.sidebar.file_uploader("Carica CSV", type="csv")
if uploaded_file:
    try:
        df_load = pd.read_csv(uploaded_file)
        new_port = {}
        for _, row in df_load.iterrows():
            t = str(row['Ticker'])
            new_port[t] = {
                'Nome': row.get('Nome', t),
                'ISIN': get_clean_isin(row.get('ISIN', '')),
                'Politica': str(row.get('Politica', 'Acc')),
                'TER': str(row.get('TER', '')).replace("nan", ""),
                'Peso': float(row.get('Peso', 0)),
                'Prezzo': float(row.get('Prezzo', 0)),
                'Valuta': row.get('Valuta', 'EUR'),
                'Cambio': float(row.get('Cambio', 1.0))
            }
        st.session_state.portfolio = new_port
    except: st.sidebar.error("Errore caricamento CSV.")

if st.session_state.portfolio:
    df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
    st.sidebar.download_button("📥 Esporta CSV", df_save.to_csv(index=False).encode('utf-8'), "pac_etf.csv")

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget))

st.sidebar.subheader("➕ Aggiungi ETF")
new_ticker = st.sidebar.text_input("Ticker Yahoo (es: SWDA.MI)")
if st.sidebar.button("Aggiungi"):
    if new_ticker:
        t_up = new_ticker.upper().strip()
        try:
            with st.spinner("Recupero dati..."):
                y_info = yf.Ticker(t_up).info
                isin = get_clean_isin(y_info.get('isin', ''))
                st.session_state.portfolio[t_up] = {
                    'Nome': y_info.get('longName', t_up),
                    'ISIN': isin,
                    'Politica': 'Dist' if y_info.get('dividendYield', 0) > 0 else 'Acc',
                    'TER': f"{y_info.get('annualReportExpenseRatio', 0.2)*100:.2f}%" if y_info.get('annualReportExpenseRatio') else "0.20%",
                    'Peso': 0.0,
                    'Prezzo': float(y_info.get('currentPrice') or y_info.get('previousClose') or 0),
                    'Valuta': y_info.get('currency', 'EUR'),
                    'Cambio': get_exchange_rate(y_info.get('currency', 'EUR'))
                }
                st.rerun()
        except: st.sidebar.error("Ticker non trovato.")

# --- MAIN ---
st.title("💰 ETF PAC Planner")

if st.session_state.portfolio:
    # Intestazioni Colonne
    cols = st.columns([3.5, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
    header_labels = ["Dati ETF / JustETF", "Politica / TER", "Prezzo €", "Peso %", "Investimento", "Quote", ""]
    for col, lab in zip(cols, header_labels): col.write(f"**{lab}**")

    tot_w = 0
    for ticker, asset in st.session_state.portfolio.items():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3.5, 1.2, 1.0, 1.0, 1.3, 1.3, 0.4])
        
        # 1. NOME, TICKER, ISIN E LINK (Puliti da N/A)
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:60]}</div>", unsafe_allow_html=True)
            
            isin = asset.get('ISIN', '')
            # Sottotitolo con Ticker ed eventualmente ISIN (solo se valido)
            meta_html = f"<div class='etf-meta'>{ticker}"
            if isin:
                meta_html += f" | <span class='isin-code'>{isin}</span>"
            meta_html += "</div>"
            st.markdown(meta_html, unsafe_allow_html=True)
            
            # COSTRUZIONE LINK (Senza N/A)
            if isin:
                # Se abbiamo l'ISIN, link diretto sicuro
                just_url = f"https://www.justetf.com/it/etf-profile.html?isin={isin}"
                link_label = "Vedi Scheda JustETF"
            else:
                # Se l'ISIN manca, link alla ricerca per Nome
                search_term = urllib.parse.quote(asset['Nome'])
                just_url = f"https://www.justetf.com/it/find-etf.html?query={search_term}"
                link_label = "Cerca su JustETF"
            
            st.markdown(f"<a href='{just_url}' target='_blank' class='just-link'>🔗 {link_label}</a>", unsafe_allow_html=True)

        # 2. POLICY / TER
        with c2:
            pol = st.selectbox("Tipo", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"p_{ticker}", label_visibility="collapsed")
            st.session_state.portfolio[ticker]['Politica'] = pol
            ter = st.text_input("TER", asset.get('TER', ''), key=f"t_{ticker}", label_visibility="collapsed", placeholder="TER %")
            st.session_state.portfolio[ticker]['TER'] = ter

        # 3. PREZZO
        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        c3.write(f"**{p_eur:.2f} €**")

        # 4. PESO %
        w = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        st.session_state.portfolio[ticker]['Peso'] = w
        tot_w += w

        # 5. INVESTIMENTO
        inv = (w / 100) * st.session_state.total_budget
        c5.markdown(f"<span class='euro-value'>{inv:,.2f} €</span>", unsafe_allow_html=True)

        # 6. QUOTE
        q = inv / p_eur if p_eur > 0 else 0
        c6.write(f"**{q:.2f}**")

        # 7. DELETE
        if c7.button("🗑️", key=f"d_{ticker}"):
            del st.session_state.portfolio[ticker]
            st.rerun()

    st.markdown("---")
    if tot_w != 100: st.warning(f"Allocazione budget attuale: {tot_w}% (deve essere 100%)")
    else: st.success("✅ Budget 100% allocato correttamente.")
    
    # Grafico a torta
    df_plot = pd.DataFrame([{'ETF': k, 'Peso': v['Peso']} for k,v in st.session_state.portfolio.items() if v['Peso']>0])
    if not df_plot.empty:
        st.plotly_chart(px.pie(df_plot, values='Peso', names='ETF', hole=0.4), use_container_width=True)
else:
    st.info("👈 Inizia aggiungendo un ticker Yahoo (es. SWDA.MI) o caricando un file CSV.")
