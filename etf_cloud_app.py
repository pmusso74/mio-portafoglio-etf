import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import urllib.parse
import re
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner Pro", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv"

# --- CSS ESTETICA ---
st.markdown("""
    <style>
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 1.1rem; }
    .isin-display { color: #d32f2f; font-weight: bold; font-family: monospace; font-size: 0.9rem; margin-bottom: 5px; }
    .real-status { color: #666; font-size: 0.85rem; font-style: italic; background: #f8f9fa; padding: 2px 5px; border-radius: 4px; border-left: 3px solid #2e7d32; }
    .search-container { background-color: #f0f7ff; padding: 15px; border-radius: 10px; border: 1px solid #1a73e8; margin-bottom: 20px; }
    .just-link-btn { 
        display: inline-block; margin-top: 8px; padding: 6px 18px; 
        background-color: #ffffff; color: #1a73e8 !important; 
        text-decoration: none !important; border: 1px solid #1a73e8;
        border-radius: 20px; font-size: 0.75rem; font-weight: 700; 
        text-transform: uppercase; transition: all 0.3s ease;
    }
    .just-link-btn:hover { background-color: #1a73e8; color: white !important; }
    .euro-value { color: #2e7d32; font-weight: 700; font-size: 1.05rem; }
    .weekly-value { color: #1a73e8; font-weight: 700; font-size: 1.05rem; }
    .pos-ret { color: #2e7d32; font-weight: 700; }
    .neg-ret { color: #d32f2f; font-weight: 700; }
    .small-metric-label { font-size: 0.9rem; color: #5f6368; font-weight: 500; }
    .small-metric-value { font-size: 1.25rem; font-weight: 800; color: #1a1c1e; }
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

def update_all_prices():
    if not st.session_state.portfolio: return
    with st.spinner("Aggiornamento prezzi..."):
        for ticker in st.session_state.portfolio:
            try:
                y_obj = yf.Ticker(ticker)
                inf = y_obj.info
                new_p = inf.get('currentPrice') or inf.get('regularMarketPrice') or inf.get('previousClose')
                if new_p: st.session_state.portfolio[ticker]['Prezzo'] = float(new_p)
                if inf.get('previousClose'): st.session_state.portfolio[ticker]['PrevClose'] = float(inf.get('previousClose'))
                st.session_state.portfolio[ticker]['Cambio'] = get_exchange_rate(st.session_state.portfolio[ticker]['Valuta'])
            except: continue
        st.toast("✅ Dati aggiornati!")

def load_from_df(df):
    df = df.fillna(0)
    new_port = {}
    for _, row in df.iterrows():
        t = str(row['Ticker']).upper()
        new_port[t] = {
            'Nome': row.get('Nome', t), 'ISIN': str(row.get('ISIN', '')),
            'Politica': str(row.get('Politica', 'Acc')), 'TER': str(row.get('TER', '')),
            'Peso': float(row.get('Peso', 0)), 'Prezzo': float(row.get('Prezzo', 0)),
            'PrevClose': float(row.get('PrevClose', row.get('Prezzo', 0))),
            'Valuta': str(row.get('Valuta', 'EUR')), 'Cambio': float(row.get('Cambio', 1.0)),
            'Investito_Reale': float(row.get('Investito_Reale', 0.0)),
            'Quote_Reali': float(row.get('Quote_Reali', 0.0))
        }
    st.session_state.portfolio = new_port
    if 'Total_Budget' in df.columns: st.session_state.total_budget = float(df['Total_Budget'].iloc[0])

def save_data_locally():
    if st.session_state.portfolio:
        df_save = pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()])
        df_save.to_csv(DB_FILE, index=False)
        return True
    return False

@st.cache_data(ttl=300)
def fetch_historical_data(tickers):
    if not tickers: return pd.DataFrame()
    data = yf.download(list(tickers), period="1y", progress=False)['Close']
    if len(tickers) == 1: data = data.to_frame(); data.columns = list(tickers)
    return data.ffill().dropna()

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    if os.path.exists(DB_FILE):
        try: load_from_df(pd.read_csv(DB_FILE))
        except: pass
if 'total_budget' not in st.session_state: st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.title("📁 Gestione Portafoglio")
cs1, cs2 = st.sidebar.columns(2)
if cs1.button("💾 SALVA", help="Salva piano e quote reali"):
    if save_data_locally(): st.sidebar.success("Salvato!")
if cs2.button("🔄 AGGIORNA", help="Aggiorna prezzi ora"):
    update_all_prices()
    st.rerun()

uploaded_file = st.sidebar.file_uploader("📥 Carica CSV", type="csv")
if uploaded_file:
    load_from_df(pd.read_csv(uploaded_file))
    st.rerun()

st.sidebar.markdown("---")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", min_value=0.0, value=float(st.session_state.total_budget), step=50.0)

st.sidebar.markdown("<div class='search-container'>", unsafe_allow_html=True)
target_isin = st.sidebar.text_input("Inserisci ISIN").strip().upper()
if st.sidebar.button("CERCA E AGGIUNGI"):
    if target_isin:
        try:
            with st.spinner("Ricerca..."):
                y_obj = yf.Ticker(target_isin)
                inf = y_obj.info
                st.session_state.portfolio[y_obj.ticker] = {
                    'Nome': inf.get('longName', y_obj.ticker), 'ISIN': target_isin,
                    'Politica': 'Acc', 'TER': '0.20%', 'Peso': 0.0,
                    'Prezzo': float(inf.get('currentPrice') or inf.get('previousClose')),
                    'PrevClose': float(inf.get('previousClose') or 0),
                    'Valuta': inf.get('currency', 'EUR'), 'Cambio': get_exchange_rate(inf.get('currency', 'EUR')),
                    'Investito_Reale': 0.0, 'Quote_Reali': 0.0
                }
                st.rerun()
        except: st.sidebar.error("ISIN non trovato.")
st.sidebar.markdown("</div>", unsafe_allow_html=True)

# --- MAIN ---
st.title("💰 Il mio Piano d'Accumulo")

if st.session_state.portfolio:
    cols = st.columns([2.5, 0.9, 0.8, 0.7, 1.0, 1.0, 0.8, 1.0])
    labels = ["Asset / JustETF", "Dati", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Quote S.", "Azioni"]
    for col, lab in zip(cols, labels): col.write(f"**{lab}**")

    tot_w, total_invested_all, current_value_all = 0, 0, 0
    all_tickers = list(st.session_state.portfolio.keys())

    for ticker, asset in st.session_state.portfolio.items():
        if 'Investito_Reale' not in asset: asset['Investito_Reale'] = 0.0
        if 'Quote_Reali' not in asset: asset['Quote_Reali'] = 0.0

        p_eur = asset['Prezzo'] * asset.get('Cambio', 1.0)
        inv_m = (asset['Peso'] / 100) * st.session_state.total_budget
        inv_w = inv_m / 4.33
        
        val_attuale_asset = asset['Quote_Reali'] * p_eur
        total_invested_all += asset['Investito_Reale']
        current_value_all += val_attuale_asset

        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.5, 0.9, 0.8, 0.7, 1.0, 1.0, 0.8, 1.0])
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:40]}</div><div class='isin-display'>{asset['ISIN']}</div>", unsafe_allow_html=True)
            if asset['Investito_Reale'] > 0:
                diff = val_attuale_asset - asset['Investito_Reale']
                st.markdown(f"<div class='real-status'>Posseduto: {val_attuale_asset:,.2f}€ ({(diff):+,.2f}€)</div>", unsafe_allow_html=True)
            st.markdown(f"<a href='https://www.justetf.com/it/etf-profile.html?isin={asset['ISIN']}' target='_blank' class='just-link-btn'>JustETF</a>", unsafe_allow_html=True)

        with c2:
            asset['Politica'] = st.selectbox("T", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"p_{ticker}", label_visibility="collapsed")
            asset['TER'] = st.text_input("T", asset['TER'], key=f"t_{ticker}", label_visibility="collapsed")

        c3.write(f"**{p_eur:.2f}**")
        asset['Peso'] = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        tot_w += asset['Peso']
        c5.markdown(f"<span class='euro-value'>{inv_m:,.2f}</span>", unsafe_allow_html=True)
        c6.markdown(f"<span class='weekly-value'>{inv_w:,.2f}</span>", unsafe_allow_html=True)
        c7.write(f"{inv_w/p_eur if p_eur>0 else 0:.2f}")

        with c8:
            act = st.columns(3)
            if act[0].button("➕", key=f"b_{ticker}", help="Registra acquisto settimanale"):
                asset['Investito_Reale'] += inv_w
                asset['Quote_Reali'] += (inv_w / p_eur) if p_eur > 0 else 0
                st.rerun()
            if act[1].button("➖", key=f"r_{ticker}", help="Storna ultima quota"):
                if asset['Investito_Reale'] >= inv_w:
                    asset['Investito_Reale'] -= inv_w
                    asset['Quote_Reali'] = max(0.0, asset['Quote_Reali'] - (inv_w / p_eur))
                    st.rerun()
            if act[2].button("🗑️", key=f"d_{ticker}"):
                del st.session_state.portfolio[ticker]; st.rerun()

    st.markdown("---")

    # --- RIEPILOGO REALE ---
    if total_invested_all > 0:
        st.subheader("🏦 Stato Portafoglio Reale")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Capitale Versato", f"{total_invested_all:,.2f} €")
        r2.metric("Valore Attuale", f"{current_value_all:,.2f} €")
        r3.metric("Profit & Loss", f"{(current_value_all - total_invested_all):+,.2f} €", f"{((current_value_all/total_invested_all)-1)*100:+.2f}%")
        if r4.button("🧹 Reset Dati Reali"):
            for t in st.session_state.portfolio:
                st.session_state.portfolio[t]['Investito_Reale'] = 0.0
                st.session_state.portfolio[t]['Quote_Reali'] = 0.0
            st.rerun()

    # --- ANALISI STORICA E ODIERNA ---
    active_tickers = [t for t in all_tickers if st.session_state.portfolio[t]['Peso'] > 0]
    if active_tickers:
        try:
            data = fetch_historical_data(tuple(all_tickers))
            if not data.empty:
                tot_w_ins = sum(st.session_state.portfolio[t]['Peso'] for t in active_tickers)
                norm = (data / data.iloc[0]) * 100
                port_line = pd.Series(0.0, index=norm.index)
                for t in active_tickers:
                    port_line += norm[t] * (st.session_state.portfolio[t]['Peso'] / tot_w_ins)
                
                # Calcolo oggi
                today_data = []
                pac_today_ret = 0
                for t in active_tickers:
                    asset = st.session_state.portfolio[t]
                    change = ((asset['Prezzo'] / asset['PrevClose']) - 1) * 100 if asset.get('PrevClose', 0) > 0 else 0
                    today_data.append({'Asset': asset['Nome'][:30], 'Variazione %': change})
                    pac_today_ret += change * (asset['Peso'] / tot_w_ins)
                today_data.append({'Asset': '⭐ IL TUO PAC (TOTALE)', 'Variazione %': pac_today_ret})

                m1, m2, m3 = st.columns(3)
                m1.markdown(f"<div class='small-metric-label'>Rendimento 1 Anno</div><div class='small-metric-value'>{port_line.iloc[-1]-100:+.2f}%</div>", unsafe_allow_html=True)
                m2.markdown(f"<div class='small-metric-label'>Rendimento 6 Mesi</div><div class='small-metric-value'>{((port_line.iloc[-1]/port_line.iloc[-len(port_line)//2])-1)*100:+.2f}%</div>", unsafe_allow_html=True)
                m3.markdown(f"<div class='small-metric-label'>Variazione Oggi</div><div class='small-metric-value' style='color:{'#2e7d32' if pac_today_ret>=0 else '#d32f2f'}'>{pac_today_ret:+.2f}%</div>", unsafe_allow_html=True)

                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=port_line.index, y=port_line, name="IL TUO PAC", line=dict(color='#FF3B30', width=5)))
                for t in active_tickers:
                    fig1.add_trace(go.Scatter(x=norm.index, y=norm[t], name=st.session_state.portfolio[t]['Nome'][:20], line=dict(width=1.5), opacity=0.8))
                fig1.update_layout(title="Andamento Storico 1 Anno", template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig1, use_container_width=True)

                st.subheader("📊 Performance Odierna")
                fig2 = px.bar(pd.DataFrame(today_data), x='Variazione %', y='Asset', orientation='h', color='Variazione %', color_continuous_scale='RdYlGn', range_color=[-2, 2], text_auto='.2f')
                fig2.update_layout(template="plotly_white", showlegend=False, height=300)
                st.plotly_chart(fig2, use_container_width=True)

                for t in active_tickers:
                    r1a, r6m = ((data[t].iloc[-1]/data[t].iloc[0])-1)*100, ((data[t].iloc[-1]/data[t].iloc[-len(data)//2])-1)*100
                    ca, cb, cc, cd = st.columns([3, 1, 1, 2])
                    ca.write(f"**{st.session_state.portfolio[t]['Nome']}**")
                    cb.markdown(f"<span class='{'pos-ret' if r1a>=0 else 'neg-ret'}'>1A: {r1a:+.2f}%</span>", unsafe_allow_html=True)
                    cc.markdown(f"<span class='{'pos-ret' if r6m>=0 else 'neg-ret'}'>6M: {r6m:+.2f}%</span>", unsafe_allow_html=True)
                    cd.write(f"{data[t].iloc[0]:.2f}€ → {data[t].iloc[-1]:.2f}€")
        except: st.error("Errore analisi.")
else:
    st.info("👈 Inserisci un ISIN per iniziare.")
