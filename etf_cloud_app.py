import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ETF PAC Planner Pro", layout="wide", page_icon="💰")
DB_FILE = "pac_data.csv"
UPDATE_INTERVAL = 600 # 10 minuti per evitare flickering e blocchi Yahoo

# --- INIZIALIZZAZIONE STATO ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0.0
if 'total_budget' not in st.session_state:
    st.session_state.total_budget = 1000.0

# --- FUNZIONI ---
def detect_policy(inf, nome):
    y_val = inf.get('dividendYield') or inf.get('trailingAnnualDividendYield') or 0
    return "Dist" if y_val > 0 or "dist" in nome.lower() else "Acc"

def update_all_prices():
    if not st.session_state.portfolio: return
    for ticker in list(st.session_state.portfolio.keys()):
        try:
            y = yf.Ticker(ticker); i = y.info
            p = i.get('currentPrice') or i.get('regularMarketPrice')
            if p:
                st.session_state.portfolio[ticker]['Prezzo'] = float(p)
                st.session_state.portfolio[ticker]['Politica'] = detect_policy(i, st.session_state.portfolio[ticker]['Nome'])
        except: continue
    st.session_state.last_update = time.time()

# --- AUTO UPDATE ---
if (time.time() - st.session_state.last_update) > UPDATE_INTERVAL:
    update_all_prices()

# --- CSS ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #eee; }
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 0.95rem; line-height: 1.1; }
    .ticker-label { color: #666; font-family: monospace; font-size: 0.8rem; }
    .tipo-tag { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; color: white; }
    .acc-tag { background-color: #1a73e8; }
    .dist-tag { background-color: #f29900; }
    .real-status { color: #2e7d32; font-size: 0.75rem; font-weight: 600; margin-top: 3px; }
    .just-link-btn { 
        display: inline-block; margin-top: 5px; padding: 2px 10px; 
        background-color: #ffffff; color: #1a73e8 !important; 
        text-decoration: none !important; border: 1px solid #1a73e8;
        border-radius: 4px; font-size: 0.65rem; font-weight: 700;
    }
    .budget-box { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #1a73e8; margin-bottom: 20px; }
    .weight-warning { color: #d32f2f; font-weight: bold; font-size: 1.1rem; }
    .weight-ok { color: #2e7d32; font-weight: bold; font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.header("📊 Configurazione")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0)

with st.sidebar.expander("➕ Aggiungi ETF", expanded=True):
    new_t = st.text_input("Ticker Yahoo (es. SWDA.MI)").strip().upper()
    if st.button("Aggiungi Asset"):
        try:
            y = yf.Ticker(new_t); i = y.info; n = i.get('shortName', new_t)
            st.session_state.portfolio[new_t] = {
                'Nome': n, 'ISIN': i.get('underlyingSymbol') or (y.isin if hasattr(y, 'isin') else ""),
                'Politica': detect_policy(i, n), 'TER': '0.20%', 'Peso': 0.0,
                'Prezzo': i.get('currentPrice') or i.get('regularMarketPrice'),
                'PrevClose': i.get('previousClose', 0), 'Valuta': i.get('currency', 'EUR'),
                'Cambio': 1.0, 'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            st.rerun()
        except: st.error("Non trovato")

st.sidebar.markdown("---")
if st.sidebar.button("💾 SALVA DATI", use_container_width=True):
    pd.DataFrame([{'Ticker': k, 'Total_Budget': st.session_state.total_budget, **v} for k, v in st.session_state.portfolio.items()]).to_csv(DB_FILE, index=False)
    st.sidebar.success("Salvato!")

if st.sidebar.button("🔄 AGGIORNA ORA", use_container_width=True):
    update_all_prices(); st.rerun()

# --- MAIN ---
st.title("💰 ETF PAC Planner Pro")

if not st.session_state.portfolio:
    st.info("Aggiungi un ETF dalla barra laterale per iniziare.")
else:
    # Calcolo Somma Pesi
    somma_pesi = sum(a['Peso'] for a in st.session_state.portfolio.values())
    
    # Avviso Pesi
    if somma_pesi != 100:
        st.markdown(f"⚠️ <span class='weight-warning'>Attenzione: La somma dei pesi è {somma_pesi}% (Deve essere 100% per un calcolo Drift corretto)</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"✅ <span class='weight-ok'>Configurazione Pesi Corretta: {somma_pesi}%</span>", unsafe_allow_html=True)

    # Tabella
    h = st.columns([2.2, 0.6, 0.7, 0.7, 0.9, 0.9, 0.7, 1.2])
    for col, text in zip(h, ["Asset", "Tipo", "Prezzo €", "Peso %", "Mensile €", "Settim. €", "Drift", "Azioni"]): col.write(f"**{text}**")

    total_val_portafoglio = sum(a['Quote_Reali'] * a['Prezzo'] * a['Cambio'] for a in st.session_state.portfolio.values())
    
    for ticker, asset in list(st.session_state.portfolio.items()):
        p_eur = asset['Prezzo'] * asset['Cambio']
        target_eur = (asset['Peso'] / 100) * st.session_state.total_budget
        target_settim = target_eur / 4.33
        v_attuale = asset['Quote_Reali'] * p_eur
        
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.2, 0.6, 0.7, 0.7, 0.9, 0.9, 0.7, 1.2])
        with c2: st.markdown(f"<span class='tipo-tag {'acc-tag' if asset['Politica']=='Acc' else 'dist-tag'}'>{asset['Politica']}</span>", unsafe_allow_html=True)
        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:35]}</div><div class='ticker-label'>{ticker}</div>", unsafe_allow_html=True)
            if v_attuale > 0: st.markdown(f"<div class='real-status'>Valore: {v_attuale:,.2f}€</div>", unsafe_allow_html=True)
            
            # --- LOGICA JUSTETF ---
            isin_to_use = asset.get('ISIN', '')
            if not isin_to_use or len(str(isin_to_use)) < 10 or isin_to_use == "-":
                just_etf_url = f"https://www.justetf.com/it/find-etf.html?query={ticker.split('.')[0]}"
            else:
                just_etf_url = f"https://www.justetf.com/it/etf-profile.html?isin={isin_to_use}"
            st.markdown(f"<a href='{just_etf_url}' target='_blank' class='just-link-btn'>JustETF ↗</a>", unsafe_allow_html=True)

        c3.write(f"{p_eur:,.2f}")
        asset['Peso'] = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        
        c5.write(f"**{target_eur:,.2f}**")
        c6.write(f"{target_settim:,.2f}")
        
        with c7:
            if total_val_portafoglio > 0:
                drift = ((v_attuale / total_val_portafoglio) * 100) - asset['Peso']
                st.write(f"{drift:+.1f}%")
            else: st.write("-")

        with c8:
            act1, act2, act3 = st.columns(3)
            if act1.button("➕", key=f"add_{ticker}"):
                asset['Investito_Reale'] += target_eur
                asset['Quote_Reali'] += (target_eur / p_eur) if p_eur > 0 else 0
                st.rerun()
            if act2.button("➖", key=f"sub_{ticker}"):
                if asset['Investito_Reale'] >= target_eur:
                    asset['Investito_Reale'] -= target_eur
                    asset['Quote_Reali'] = max(0, asset['Quote_Reali'] - (target_eur / p_eur))
                    st.rerun()
            if act3.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]; st.rerun()

    # --- RIEPILOGO INVESTIMENTO (SPOSTATO IN ALTO RISPETTO AL GRAFICO) ---
    st.markdown("---")
    tot_investito_reale = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Versato", f"{tot_investito_reale:,.2f} €")
    m2.metric("Valore Attuale", f"{total_val_portafoglio:,.2f} €")
    m3.metric("Profit/Loss", f"{total_val_portafoglio - tot_investito_reale:,.2f} €", f"{((total_val_portafoglio/tot_investito_reale)-1)*100 if tot_investito_reale>0 else 0:+.2f}%")

    st.markdown("---")
    c_info, c_pie = st.columns([1, 1.5])
    
    with c_info:
        st.subheader("🏦 Stato dell'Investimento")
        st.markdown("<div class='budget-box'>", unsafe_allow_html=True)
        st.write(f"**Somma Pesi impostata:** {somma_pesi}%")
        st.write(f"**Capitale Totale Versato:** {tot_investito_reale:,.2f} €")
        st.write(f"**Budget Mensile PAC:** {st.session_state.total_budget:,.2f} €")
        
        rapporto = tot_investito_reale / st.session_state.total_budget if st.session_state.total_budget > 0 else 0
        st.write(f"**Copertura Piano:** Hai accumulato **{rapporto:.1f} mensilità**.")
        st.progress(min(rapporto / 24, 1.0), text="Progresso (Target 2 anni)")
        st.markdown("</div>", unsafe_allow_html=True)

    with c_pie:
        if total_val_portafoglio > 0:
            df_pie = pd.DataFrame([{'Asset': a['Nome'], 'Valore': a['Quote_Reali'] * a['Prezzo'] * a['Cambio']} for a in st.session_state.portfolio.values() if a['Quote_Reali'] > 0])
            fig_p = px.pie(df_pie, values='Valore', names='Asset', hole=0.4, title="Suddivisione Reale Portafoglio (€)")
            fig_p.update_traces(textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Valore: %{value:,.2f} €')
            fig_p.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_p, use_container_width=True)

    # --- GRAFICO STORICO (SPOSTATO IN FONDO) ---
    st.subheader("📈 Performance Storica (1 Anno)")
    try:
        tks = list(st.session_state.portfolio.keys())
        data = yf.download(tks, period="1y", progress=False)['Close']
        if len(tks) == 1: data = data.to_frame(); data.columns = tks
        norm = (data.ffill() / data.ffill().iloc[0]) * 100
        fig = go.Figure()
        pesi_grafico = [st.session_state.portfolio[t]['Peso'] for t in tks]
        if sum(pesi_grafico) > 0:
            fig.add_trace(go.Scatter(x=norm.index, y=(norm * pesi_grafico).sum(axis=1)/sum(pesi_grafico), name="⭐ IL TUO PAC", line=dict(color='red', width=4), zorder=10))
        for t in tks:
            fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=st.session_state.portfolio[t]['Nome'][:20], line=dict(width=1.5), opacity=0.6))
        fig.update_layout(template="plotly_white", height=400, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)
    except: st.warning("Grafico storico non disponibile")

st.sidebar.caption(f"Ultimo agg: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_update))}")
