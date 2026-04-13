import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner Pro v2", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv"
UPDATE_INTERVAL = 600 

# --- FUNZIONI DI PERSISTENZA (AUTOSAVE) ---
def save_data():
    """Salva lo stato attuale del portafoglio su file CSV."""
    if st.session_state.portfolio:
        data_to_save = []
        for ticker, asset in st.session_state.portfolio.items():
            row = {'Ticker': ticker, 'Total_Budget': st.session_state.total_budget}
            row.update(asset)
            data_to_save.append(row)
        pd.DataFrame(data_to_save).to_csv(DB_FILE, index=False)

def load_data():
    """Carica i dati dal file CSV all'avvio."""
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if not df.empty:
                st.session_state.total_budget = float(df['Total_Budget'].iloc[0])
                new_portfolio = {}
                for _, row in df.iterrows():
                    ticker = row['Ticker']
                    asset_data = row.to_dict()
                    del asset_data['Ticker']
                    del asset_data['Total_Budget']
                    new_portfolio[ticker] = asset_data
                st.session_state.portfolio = new_portfolio
        except Exception as e:
            st.error(f"Errore nel caricamento dati: {e}")

# --- CACHING PER PERFORMANCE ---
@st.cache_data(ttl=3600)
def get_historical_data(tickers):
    """Scarica i dati storici con cache di 1 ora."""
    if not tickers: return None
    return yf.download(list(tickers), period="1y", progress=False)['Close']

@st.cache_data(ttl=86400)
def get_exchange_rate(from_currency):
    """Recupera il tasso di cambio verso EUR con cache di 24 ore."""
    if from_currency == "EUR" or not from_currency: return 1.0
    try:
        pair = f"{from_currency}EUR=X"
        ticker = yf.Ticker(pair)
        # Prova diversi metodi per ottenere il prezzo
        rate = ticker.info.get('regularMarketPrice') or ticker.fast_info.last_price
        return float(rate)
    except:
        return 1.0

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    load_data()  # Caricamento iniziale
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0.0
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- CALLBACKS ---
def sync_weight(ticker):
    """Sincronizza il peso modificato e salva."""
    st.session_state.portfolio[ticker]['Peso'] = float(st.session_state[f"input_w_{ticker}"])
    save_data()

# --- FUNZIONI CORE ---
def detect_policy(inf, nome):
    y_val = inf.get('dividendYield') or inf.get('trailingAnnualDividendYield') or 0
    return "Dist" if y_val > 0 or "dist" in nome.lower() else "Acc"

def update_all_prices():
    """Aggiorna prezzi e cambi per tutti gli asset."""
    if not st.session_state.portfolio: return
    for ticker in list(st.session_state.portfolio.keys()):
        try:
            y = yf.Ticker(ticker); i = y.info
            p = i.get('currentPrice') or i.get('regularMarketPrice') or i.get('previousClose')
            curr = i.get('currency', 'EUR')
            if p:
                st.session_state.portfolio[ticker]['Prezzo'] = float(p)
                st.session_state.portfolio[ticker]['Valuta'] = curr
                st.session_state.portfolio[ticker]['Cambio'] = get_exchange_rate(curr)
                st.session_state.portfolio[ticker]['Nome'] = i.get('shortName', ticker)
                st.session_state.portfolio[ticker]['Politica'] = detect_policy(i, st.session_state.portfolio[ticker]['Nome'])
        except: continue
    st.session_state.last_update = time.time()
    save_data()

# Auto-update se l'intervallo è superato
if (time.time() - st.session_state.last_update) > UPDATE_INTERVAL:
    update_all_prices()

# --- CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #eee; }
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 0.9rem; line-height: 1.1; }
    .ticker-label { color: #666; font-family: monospace; font-size: 0.75rem; }
    .tipo-tag { padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white; }
    .acc-tag { background-color: #1a73e8; }
    .dist-tag { background-color: #f29900; }
    .rebalance-hint { color: #1a73e8; font-weight: bold; font-size: 0.85rem; background: #e8f0fe; padding: 4px 8px; border-radius: 4px; border: 1px solid #d2e3fc; }
    .just-link { font-size: 0.7rem; color: #1a73e8; text-decoration: none; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("📊 Configurazione")
old_budget = st.session_state.total_budget
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0)
if old_budget != st.session_state.total_budget:
    save_data()

with st.sidebar.expander("➕ Aggiungi ETF", expanded=False):
    new_t = st.text_input("Ticker Yahoo (es. SWDA.MI)").strip().upper()
    if st.button("Aggiungi Asset"):
        try:
            y = yf.Ticker(new_t); i = y.info
            n = i.get('shortName', new_t)
            curr = i.get('currency', 'EUR')
            st.session_state.portfolio[new_t] = {
                'Nome': n, 'ISIN': i.get('underlyingSymbol') or (y.isin if hasattr(y, 'isin') else ""),
                'Politica': detect_policy(i, n), 'TER': '0.20%', 'Peso': 0.0,
                'Prezzo': i.get('currentPrice') or i.get('regularMarketPrice') or i.get('previousClose'),
                'Valuta': curr, 'Cambio': get_exchange_rate(curr),
                'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            save_data(); st.rerun()
        except: st.error("Ticker non trovato")

if st.sidebar.button("🔄 AGGIORNA PREZZI", use_container_width=True):
    update_all_prices(); st.rerun()

if st.sidebar.button("🧹 RESET PORTAFOGLIO", use_container_width=True):
    st.session_state.portfolio = {}; save_data(); st.rerun()

# --- LOGICA SMART REBALANCING ---
# Calcola come allocare il budget per minimizzare il drift
total_val_attuale = sum(a['Quote_Reali'] * a['Prezzo'] * a['Cambio'] for a in st.session_state.portfolio.values())
target_val_finale = total_val_attuale + st.session_state.total_budget

allocazione_smart = {}
if st.session_state.portfolio:
    for t, a in st.session_state.portfolio.items():
        valore_target_ideale = target_val_finale * (a['Peso'] / 100)
        valore_attuale_eur = a['Quote_Reali'] * a['Prezzo'] * a['Cambio']
        differenza = valore_target_ideale - valore_attuale_eur
        allocazione_smart[t] = max(0, differenza)

    # Normalizzazione per non eccedere il budget mensile
    somma_suggerimenti = sum(allocazione_smart.values())
    if somma_suggerimenti > st.session_state.total_budget and somma_suggerimenti > 0:
        ratio = st.session_state.total_budget / somma_suggerimenti
        for t in allocazione_smart: allocazione_smart[t] *= ratio

# --- MAIN UI ---
st.title("💰 ETF PAC Planner Pro v2")

if not st.session_state.portfolio:
    st.info("Benvenuto! Aggiungi un ETF dal menu laterale per configurare il tuo piano.")
else:
    # Controllo Pesi
    somma_pesi = round(sum(float(a['Peso']) for a in st.session_state.portfolio.values()), 2)
    if somma_pesi != 100.0:
        st.warning(f"⚠️ La somma dei pesi è {somma_pesi}%. Deve essere 100% per un calcolo corretto.")
    else:
        st.success(f"✅ Portafoglio bilanciato (100%)")

    # Tabella Asset
    h = st.columns([2, 0.6, 0.8, 0.8, 1.2, 0.8, 1.2])
    cols_labels = ["Asset / ISIN", "Tipo", "Prezzo €", "Peso %", "Smart Buy €", "Drift", "Azioni"]
    for col, text in zip(h, cols_labels): col.write(f"**{text}**")

    for ticker, asset in list(st.session_state.portfolio.items()):
        p_eur = asset['Prezzo'] * asset['Cambio']
        v_attuale_eur = asset['Quote_Reali'] * p_eur
        
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 0.6, 0.8, 0.8, 1.2, 0.8, 1.2])
        
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:35]}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='ticker-label'>{ticker} | {asset.get('ISIN','-')}</div>", unsafe_allow_html=True)
            url = f"https://www.justetf.com/it/etf-profile.html?isin={asset.get('ISIN','')}"
            st.markdown(f"<a href='{url}' target='_blank' class='just-link'>Dettagli JustETF ↗</a>", unsafe_allow_html=True)

        c2.markdown(f"<br><span class='tipo-tag {'acc-tag' if asset['Politica']=='Acc' else 'dist-tag'}'>{asset['Politica']}</span>", unsafe_allow_html=True)
        c3.write(f"<br>{p_eur:,.2f}", unsafe_allow_html=True)
        
        c4.number_input("%", 0.0, 100.0, float(asset['Peso']), step=1.0, key=f"input_w_{ticker}", on_change=sync_weight, args=(ticker,), label_visibility="collapsed")
        
        # Smart Buy (Suggerimento Rebalancing)
        suggerito = allocazione_smart.get(ticker, 0.0)
        c5.markdown(f"<br><div class='rebalance-hint'>+ {suggerito:,.2f} €</div>", unsafe_allow_html=True)
        
        with c6:
            if total_val_attuale > 0:
                drift = ((v_attuale_eur / total_val_attuale) * 100) - asset['Peso']
                st.write(f"<br>{drift:+.1f}%", unsafe_allow_html=True)
            else: st.write("<br>-", unsafe_allow_html=True)

        with c7:
            st.write("") # Spaziatore
            act1, act2, act3 = st.columns(3)
            if act1.button("➕", key=f"add_{ticker}", help="Registra acquisto per l'importo suggerito"):
                asset['Investito_Reale'] += suggerito
                asset['Quote_Reali'] += (suggerito / p_eur) if p_eur > 0 else 0
                save_data(); st.rerun()
            if act2.button("➖", key=f"sub_{ticker}", help="Rimuovi una mensilità"):
                asset['Investito_Reale'] = max(0, asset['Investito_Reale'] - suggerito)
                asset['Quote_Reali'] = max(0, asset['Quote_Reali'] - (suggerito / p_eur))
                save_data(); st.rerun()
            if act3.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; save_data(); st.rerun()

    # --- RIEPILOGO METRICHE ---
    st.markdown("---")
    tot_investito = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_investito:,.2f} €")
    m2.metric("Valore Attuale", f"{total_val_attuale:,.2f} €")
    pnl = total_val_attuale - tot_investito
    pnl_p = (pnl / tot_investito * 100) if tot_investito > 0 else 0
    m3.metric("Profit/Loss Totale", f"{pnl:,.2f} €", f"{pnl_p:+.2f}%")

    # --- GRAFICI E PERFORMANCE ---
    st.markdown("---")
    col_chart, col_pie = st.columns([2, 1])
    
    with col_chart:
        st.subheader("📈 Performance Storica (1 Anno)")
        try:
            tks = tuple(st.session_state.portfolio.keys())
            hist_data = get_historical_data(tks)
            if hist_data is not None:
                norm = (hist_data / hist_data.iloc[0]) * 100
                fig = go.Figure()
                
                # Calcolo linea portafoglio pesata
                pesi = [st.session_state.portfolio[t]['Peso'] for t in tks]
                somma_p = sum(pesi) if sum(pesi) > 0 else 1
                portfolio_line = (norm * pesi).sum(axis=1) / somma_p
                
                fig.add_trace(go.Scatter(x=norm.index, y=portfolio_line, name="PORTAFOGLIO (Target)", line=dict(color='#1a73e8', width=3)))
                
                for t in tks:
                    fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=f"{t}", line=dict(width=1), opacity=0.3))
                
                fig.update_layout(template="plotly_white", height=400, margin=dict(l=0, r=0, t=20, b=0), legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig, use_container_width=True)
        except:
            st.info("Dati storici in fase di caricamento...")

    with col_pie:
        st.subheader("🎯 Distribuzione Reale")
        if total_val_attuale > 0:
            df_pie = pd.DataFrame([
                {'Asset': a['Nome'], 'Valore': a['Quote_Reali'] * a['Prezzo'] * a['Cambio']} 
                for a in st.session_state.portfolio.values() if a['Quote_Reali'] > 0
            ])
            if not df_pie.empty:
                fig_p = px.pie(df_pie, values='Valore', names='Asset', hole=0.4)
                fig_p.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
                st.plotly_chart(fig_p, use_container_width=True)
            else:
                st.write("Nessun investimento reale registrato. Clicca su ➕ per simulare un acquisto.")

st.sidebar.caption(f"Ultimo aggiornamento prezzi: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))}")
