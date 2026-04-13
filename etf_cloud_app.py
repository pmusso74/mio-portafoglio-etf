import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner Pro", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv"
UPDATE_INTERVAL = 600  # 10 minuti

# --- INIZIALIZZAZIONE STATO (Previene AttributeError) ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0.0
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- CARICAMENTO DATI DA FILE ---
if not st.session_state.portfolio and os.path.exists(DB_FILE):
    try:
        df = pd.read_csv(DB_FILE).fillna("")
        for _, r in df.iterrows():
            st.session_state.portfolio[r['Ticker']] = {
                'Nome': r['Nome'], 'ISIN': r['ISIN'], 'Politica': r['Politica'],
                'TER': r['TER'], 'Peso': float(r['Peso']), 'Prezzo': float(r['Prezzo']),
                'PrevClose': float(r.get('PrevClose', r['Prezzo'])), 'Valuta': r['Valuta'],
                'Cambio': float(r['Cambio']), 'Investito_Reale': float(r['Investito_Reale']),
                'Quote_Reali': float(r['Quote_Reali'])
            }
        st.session_state.total_budget = float(df['Total_Budget'].iloc[0]) if not df.empty else 1000.0
    except:
        pass

# --- CSS ESTETICA ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 0.95rem; line-height: 1.1; }
    .ticker-label { color: #666; font-family: monospace; font-size: 0.8rem; margin-bottom: 2px; }
    .tipo-tag { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; color: white; }
    .acc-tag { background-color: #1a73e8; }
    .dist-tag { background-color: #f29900; }
    .real-status { color: #2e7d32; font-size: 0.75rem; font-weight: 600; margin-top: 3px; }
    .just-link-btn { 
        display: inline-block; margin-top: 5px; padding: 3px 12px; 
        background-color: #1a73e8; color: white !important; 
        text-decoration: none !important; border-radius: 4px; 
        font-size: 0.7rem; font-weight: 700; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---
def detect_policy(inf, nome):
    yield_val = inf.get('dividendYield') or inf.get('trailingAnnualDividendYield') or 0
    if yield_val > 0: return "Dist"
    if "dist" in nome.lower(): return "Dist"
    return "Acc"

def get_exchange_rate(ticker_currency):
    if not ticker_currency or ticker_currency == "EUR": return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose')
        return float(rate) if rate else 1.0
    except: return 1.0

def update_all_prices():
    if not st.session_state.portfolio: return
    with st.spinner("Aggiornamento prezzi in corso..."):
        for ticker in list(st.session_state.portfolio.keys()):
            try:
                y_obj = yf.Ticker(ticker)
                inf = y_obj.info
                p = inf.get('currentPrice') or inf.get('regularMarketPrice')
                if p:
                    st.session_state.portfolio[ticker]['Prezzo'] = float(p)
                    st.session_state.portfolio[ticker]['PrevClose'] = float(inf.get('previousClose', p))
                    st.session_state.portfolio[ticker]['Politica'] = detect_policy(inf, st.session_state.portfolio[ticker]['Nome'])
            except: continue
        st.session_state.last_update = time.time()

# --- LOGICA AGGIORNAMENTO AUTOMATICO ---
if (time.time() - st.session_state.last_update) > UPDATE_INTERVAL:
    update_all_prices()

# --- SIDEBAR ---
st.sidebar.header("📊 Gestione Piano")
st.session_state.total_budget = st.sidebar.number_input(
    "Budget Mensile (€)", 
    value=float(st.session_state.total_budget), 
    step=50.0,
    help="Inserisci la cifra totale che intendi investire ogni mese. Verrà suddivisa tra i vari ETF in base ai pesi %."
)

with st.sidebar.expander("➕ Aggiungi ETF", expanded=True):
    new_ticker = st.text_input("Ticker Yahoo (es. SWDA.MI)", help="Usa il formato di Yahoo Finance. Esempi: SWDA.MI (Milano), SXR8.DE (Xetra).")
    if st.button("Aggiungi all'elenco", help="Cerca l'ETF e lo aggiunge alla tua tabella di pianificazione."):
        try:
            y = yf.Ticker(new_ticker)
            inf = y.info
            nome = inf.get('shortName', new_ticker)
            st.session_state.portfolio[new_ticker] = {
                'Nome': nome, 'ISIN': y.isin if hasattr(y, 'isin') and y.isin != "-" else "",
                'Politica': detect_policy(inf, nome), 'TER': '0.20%', 'Peso': 0.0,
                'Prezzo': inf.get('currentPrice') or inf.get('regularMarketPrice'),
                'PrevClose': inf.get('previousClose', 0), 'Valuta': inf.get('currency', 'EUR'),
                'Cambio': get_exchange_rate(inf.get('currency', 'EUR')),
                'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            st.rerun()
        except: st.error("Ticker non trovato.")

st.sidebar.markdown("---")
if st.sidebar.button("💾 SALVA PORTAFOGLIO", use_container_width=True, help="Salva permanentemente i pesi, i ticker e le quote reali possedute nel file locale."):
    data = []
    for k, v in st.session_state.portfolio.items():
        row = {'Ticker': k, 'Total_Budget': st.session_state.total_budget}
        row.update(v)
        data.append(row)
    pd.DataFrame(data).to_csv(DB_FILE, index=False)
    st.sidebar.success("Dati salvati con successo!")

if st.sidebar.button("🔄 AGGIORNA PREZZI ORA", use_container_width=True, help="Scarica immediatamente gli ultimi prezzi di mercato e i tassi di cambio."):
    update_all_prices()
    st.rerun()

# --- INTERFACCIA PRINCIPALE ---
st.title("💰 ETF PAC Planner")

if not st.session_state.portfolio:
    st.info("Benvenuto! Inizia aggiungendo un ETF dal menu a sinistra.")
else:
    # Tabella
    h = st.columns([2.5, 0.6, 0.8, 0.8, 1, 1, 1.2])
    headers = ["Asset", "Tipo", "Prezzo €", "Peso %", "Mensile €", "Drift", "Azioni"]
    for col, text in zip(h, headers): col.write(f"**{text}**")

    total_val = sum(a['Quote_Reali'] * a['Prezzo'] * a['Cambio'] for a in st.session_state.portfolio.values())
    
    for ticker, asset in list(st.session_state.portfolio.items()):
        p_eur = asset['Prezzo'] * asset['Cambio']
        target_eur = (asset['Peso'] / 100) * st.session_state.total_budget
        v_attuale = asset['Quote_Reali'] * p_eur
        
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2.5, 0.6, 0.8, 0.8, 1, 1, 1.2])
        
        with c2:
            tipo = asset['Politica']
            cls = "acc-tag" if tipo == "Acc" else "dist-tag"
            st.markdown(f"<span class='tipo-tag {cls}'>{tipo}</span>", unsafe_allow_html=True)

        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:40]}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='ticker-label'>{ticker}</div>", unsafe_allow_html=True)
            if v_attuale > 0:
                st.markdown(f"<div class='real-status'>Posseduto: {v_attuale:,.2f}€</div>", unsafe_allow_html=True)
            
            # Link JustETF
            if asset.get('ISIN'):
                l_url = f"https://www.justetf.com/it/etf-profile.html?isin={asset['ISIN']}"
                st.markdown(f"<a href='{l_url}' target='_blank' class='just-link-btn'>JustETF ↗</a>", unsafe_allow_html=True)

        c3.write(f"{p_eur:,.2f}")
        asset['Peso'] = c4.number_input(
            "%", 0, 100, int(asset['Peso']), 
            key=f"w_{ticker}", 
            label_visibility="collapsed",
            help="Imposta la percentuale del budget mensile da destinare a questo asset."
        )
        c5.write(f"**{target_eur:,.2f} €**")
        
        with c6:
            if total_val > 0:
                drift = ((v_attuale / total_val) * 100) - asset['Peso']
                st.write(f"{drift:+.1f}%")
            else: st.write("-")

        with c7:
            act1, act2, act3 = st.columns(3)
            if act1.button("➕", key=f"add_{ticker}", help="REGISTRA ACQUISTO: Aggiunge l'importo mensile target al capitale investito e calcola le quote caricate."):
                asset['Investito_Reale'] += target_eur
                asset['Quote_Reali'] += (target_eur / p_eur) if p_eur > 0 else 0
                st.rerun()
            if act2.button("➖", key=f"sub_{ticker}", help="STORNA ACQUISTO: Sottrae l'importo mensile target. Utile per correggere errori di inserimento."):
                if asset['Investito_Reale'] >= target_eur:
                    asset['Investito_Reale'] -= target_eur
                    asset['Quote_Reali'] = max(0, asset['Quote_Reali'] - (target_eur / p_eur))
                    st.rerun()
            if act3.button("🗑️", key=f"del_{ticker}", help="RIMUOVI ASSET: Elimina definitivamente questo ETF dal portafoglio."):
                del st.session_state.portfolio[ticker]
                st.rerun()

    # --- METRICHE ---
    st.markdown("---")
    tot_investito = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_investito:,.2f} €", help="Somma totale di tutti gli acquisti registrati (prezzo d'acquisto).")
    m2.metric("Valore Attuale", f"{total_val:,.2f} €", help="Valore di mercato odierno di tutte le quote possedute.")
    m3.metric("Profit/Loss", f"{total_val - tot_investito:,.2f} €", f"{((total_val/tot_investito)-1)*100 if tot_investito>0 else 0:+.2f}%", help="Guadagno o perdita totale (assoluto e percentuale).")

    # --- GRAFICI ---
    col_graph, col_pie = st.columns([2, 1])

    with col_graph:
        st.subheader("📈 Performance 1 Anno")
        if st.session_state.portfolio:
            tickers = list(st.session_state.portfolio.keys())
            try:
                data = yf.download(tickers, period="1y", progress=False)['Close']
                if len(tickers) == 1: data = data.to_frame(); data.columns = tickers
                data = data.ffill()
                norm = (data / data.iloc[0]) * 100
                fig = go.Figure()
                pesi = [st.session_state.portfolio[t]['Peso'] for t in tickers]
                if sum(pesi) > 0:
                    pac_line = (norm * pesi).sum(axis=1) / sum(pesi)
                    fig.add_trace(go.Scatter(x=pac_line.index, y=pac_line, name="⭐ IL TUO PAC", line=dict(color='red', width=4)))
                for t in tickers:
                    fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=st.session_state.portfolio[t]['Nome'][:20], line=dict(width=1.5), opacity=0.6))
                fig.update_layout(template="plotly_white", height=400, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.warning("Dati storici non disponibili per il grafico.")

    with col_pie:
        st.subheader("📊 Allocazione Reale")
        if total_val > 0:
            df_pie = pd.DataFrame([
                {'Asset': a['Nome'], 'Valore': a['Quote_Reali'] * a['Prezzo'] * a['Cambio']} 
                for a in st.session_state.portfolio.values() if a['Quote_Reali'] > 0
            ])
            fig_pie = px.pie(df_pie, values='Valore', names='Asset', hole=0.4)
            fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=400, showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Registra un acquisto (tasto ➕) per visualizzare la distribuzione del portafoglio.")

st.sidebar.markdown(f"**Ultimo agg:** {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))}")
