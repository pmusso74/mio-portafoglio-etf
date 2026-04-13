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
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .etf-name { color: #1a1c1e; font-weight: 700; font-size: 0.95rem; line-height: 1.1; }
    .ticker-label { color: #666; font-family: monospace; font-size: 0.8rem; margin-bottom: 2px; }
    .real-status { color: #2e7d32; font-size: 0.75rem; font-weight: 600; margin-top: 3px; }
    .just-link-btn { 
        display: inline-block; margin-top: 5px; padding: 3px 12px; 
        background-color: #1a73e8; color: white !important; 
        text-decoration: none !important; border-radius: 4px; 
        font-size: 0.7rem; font-weight: 700; text-align: center;
    }
    .just-link-btn:hover { background-color: #1557b0; }
    .just-link-missing { 
        display: inline-block; margin-top: 5px; padding: 3px 12px; 
        background-color: #f1f3f4; color: #5f6368 !important; 
        text-decoration: none !important; border-radius: 4px; 
        font-size: 0.7rem; border: 1px solid #dadce0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO ---
def get_exchange_rate(ticker_currency):
    if not ticker_currency or ticker_currency == "EUR": return 1.0
    try:
        t = yf.Ticker(f"{ticker_currency}EUR=X")
        rate = t.info.get('regularMarketPrice') or t.info.get('previousClose')
        return float(rate) if rate else 1.0
    except: return 1.0

def update_all_prices():
    if not st.session_state.portfolio: return
    for ticker in list(st.session_state.portfolio.keys()):
        try:
            y_obj = yf.Ticker(ticker)
            inf = y_obj.info
            p = inf.get('currentPrice') or inf.get('regularMarketPrice')
            if p:
                st.session_state.portfolio[ticker]['Prezzo'] = float(p)
                st.session_state.portfolio[ticker]['PrevClose'] = float(inf.get('previousClose', p))
        except: continue

def save_data():
    data = []
    for k, v in st.session_state.portfolio.items():
        row = {'Ticker': k, 'Total_Budget': st.session_state.total_budget}
        row.update(v)
        data.append(row)
    pd.DataFrame(data).to_csv(DB_FILE, index=False)

# --- INIZIALIZZAZIONE ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE).fillna("")
        for _, r in df.iterrows():
            st.session_state.portfolio[r['Ticker']] = {
                'Nome': r['Nome'], 'ISIN': r['ISIN'], 'Politica': r['Politica'],
                'TER': r['TER'], 'Peso': float(r['Peso']), 'Prezzo': float(r['Prezzo']),
                'PrevClose': float(r.get('PrevClose', r['Prezzo'])), 'Valuta': r['Valuta'],
                'Cambio': float(r['Cambio']), 'Investito_Reale': float(r['Investito_Reale']),
                'Quote_Reali': float(r['Quote_Reali'])
            }
        st.session_state.total_budget = df['Total_Budget'].iloc[0] if not df.empty else 1000.0
if 'total_budget' not in st.session_state: st.session_state.total_budget = 1000.0

# --- SIDEBAR ---
st.sidebar.header("📊 Gestione Piano")
st.session_state.total_budget = st.sidebar.number_input("Budget Mensile (€)", value=float(st.session_state.total_budget), step=50.0)

with st.sidebar.expander("➕ Aggiungi ETF"):
    new_ticker = st.text_input("Ticker Yahoo (es. SWDA.MI)").strip().upper()
    if st.button("Aggiungi"):
        try:
            y = yf.Ticker(new_ticker)
            inf = y.info
            st.session_state.portfolio[new_ticker] = {
                'Nome': inf.get('shortName', new_ticker), 'ISIN': y.isin if hasattr(y, 'isin') and y.isin != "-" else "",
                'Politica': 'Acc', 'TER': '0.20%', 'Peso': 0.0,
                'Prezzo': inf.get('currentPrice') or inf.get('regularMarketPrice'),
                'PrevClose': inf.get('previousClose', 0), 'Valuta': inf.get('currency', 'EUR'),
                'Cambio': get_exchange_rate(inf.get('currency', 'EUR')),
                'Investito_Reale': 0.0, 'Quote_Reali': 0.0
            }
            st.rerun()
        except: st.error("Ticker non valido")

if st.sidebar.button("💾 Salva Portafoglio", use_container_width=True):
    save_data()
    st.sidebar.success("Salvato!")

if st.sidebar.button("🔄 Aggiorna Prezzi", use_container_width=True):
    update_all_prices()
    st.rerun()

# --- MAIN ---
st.title("💰 ETF PAC Planner")

if not st.session_state.portfolio:
    st.info("Aggiungi un ETF dal menu a sinistra per iniziare.")
else:
    # Tabella
    h = st.columns([2.5, 1.2, 0.8, 0.8, 1, 1, 1])
    headers = ["Asset", "Dati ISIN/Tipo", "Prezzo €", "Peso %", "Mensile €", "Drift", "Azioni"]
    for col, text in zip(h, headers): col.write(f"**{text}**")

    total_val = sum(a['Quote_Reali'] * a['Prezzo'] * a['Cambio'] for a in st.session_state.portfolio.values())
    
    for ticker, asset in list(st.session_state.portfolio.items()):
        p_eur = asset['Prezzo'] * asset['Cambio']
        target_eur = (asset['Peso'] / 100) * st.session_state.total_budget
        v_attuale = asset['Quote_Reali'] * p_eur
        
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2.5, 1.2, 0.8, 0.8, 1, 1, 1])
        
        with c2:
            asset['ISIN'] = st.text_input("ISIN", asset['ISIN'], key=f"isin_{ticker}", label_visibility="collapsed", placeholder="Codice ISIN")
            asset['Politica'] = st.selectbox("P", ["Acc", "Dist"], index=0 if asset['Politica']=="Acc" else 1, key=f"pol_{ticker}", label_visibility="collapsed")

        with c1:
            st.markdown(f"<div class='etf-name'>{asset['Nome'][:40]}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='ticker-label'>{ticker}</div>", unsafe_allow_html=True)
            
            # LINK JUSTETF
            if asset['ISIN'] and len(asset['ISIN']) > 5:
                link_url = f"https://www.justetf.com/it/etf-profile.html?isin={asset['ISIN']}"
                st.markdown(f"<a href='{link_url}' target='_blank' class='just-link-btn'>Scheda JustETF</a>", unsafe_allow_html=True)
            else:
                link_url = f"https://www.justetf.com/it/find-etf.html?query={ticker.split('.')[0]}"
                st.markdown(f"<a href='{link_url}' target='_blank' class='just-link-missing'>Cerca su JustETF</a>", unsafe_allow_html=True)
            
            if v_attuale > 0:
                st.markdown(f"<div class='real-status'>Posseduto: {v_attuale:,.2f}€</div>", unsafe_allow_html=True)

        c3.write(f"{p_eur:,.2f}")
        asset['Peso'] = c4.number_input("%", 0, 100, int(asset['Peso']), key=f"w_{ticker}", label_visibility="collapsed")
        c5.write(f"**{target_eur:,.2f} €**")
        
        with c6:
            if total_val > 0:
                drift = ((v_attuale / total_val) * 100) - asset['Peso']
                st.write(f"{drift:+.1f}%")
            else: st.write("-")

        with c7:
            if st.button("➕", key=f"add_{ticker}", help="Registra acquisto"):
                asset['Investito_Reale'] += target_eur
                asset['Quote_Reali'] += (target_eur / p_eur)
                st.rerun()
            if st.button("🗑️", key=f"del_{ticker}"):
                del st.session_state.portfolio[ticker]
                st.rerun()

    # --- METRICHE ---
    st.markdown("---")
    tot_investito = sum(a['Investito_Reale'] for a in st.session_state.portfolio.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Totale Investito", f"{tot_investito:,.2f} €")
    m2.metric("Valore Portafoglio", f"{total_val:,.2f} €")
    m3.metric("P&L Totale", f"{total_val - tot_investito:,.2f} €", f"{((total_val/tot_investito)-1)*100 if tot_investito>0 else 0:+.2f}%")

    # --- GRAFICO PERFORMANCE AVANZATO ---
    st.subheader("📈 Analisi Storica Performance (1 Anno)")
    if st.session_state.portfolio:
        tickers = list(st.session_state.portfolio.keys())
        try:
            # Download dati storici
            data = yf.download(tickers, period="1y", progress=False)['Close']
            if len(tickers) == 1: 
                data = data.to_frame()
                data.columns = tickers
            
            # Pulizia e Normalizzazione a base 100
            data = data.ffill()
            norm = (data / data.iloc[0]) * 100
            
            # Inizio creazione Grafico con Figure Objects
            fig = go.Figure()
            
            # 1. Calcolo e Aggiunta Linea PAC (Somma Pesata)
            pesi_list = []
            for t in tickers:
                pesi_list.append(st.session_state.portfolio[t]['Peso'])
            
            total_peso = sum(pesi_list)
            if total_peso > 0:
                # Calcoliamo la media pesata riga per riga
                pac_line = (norm * pesi_list).sum(axis=1) / total_peso
                
                fig.add_trace(go.Scatter(
                    x=pac_line.index, 
                    y=pac_line,
                    name="⭐ IL TUO PAC (Totale)",
                    line=dict(color='red', width=4),
                    zorder=10 # Porta la linea in primo piano
                ))

            # 2. Aggiunta linee singoli Asset (usando i Nomi)
            for t in tickers:
                nome_asset = st.session_state.portfolio[t]['Nome']
                fig.add_trace(go.Scatter(
                    x=norm.index, 
                    y=norm[t],
                    name=nome_asset,
                    line=dict(width=1.5),
                    opacity=0.7
                ))

            fig.update_layout(
                template="plotly_white",
                height=500,
                legend=dict(orientation="h", y=-0.2),
                hovermode="x unified",
                yaxis_title="Rendimento (Base 100)",
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.warning(f"Dati storici non disponibili per il grafico: {e}")

    # --- ALLOCAZIONE ---
    if total_val > 0:
        st.markdown("---")
        df_pie = pd.DataFrame([{'Asset': a['Nome'], 'Valore': a['Quote_Reali'] * a['Prezzo'] * a['Cambio']} for a in st.session_state.portfolio.values() if a['Quote_Reali'] > 0])
        fig_pie = px.pie(df_pie, values='Valore', names='Asset', title="Distribuzione Reale Portafoglio", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

st.caption("Nota: La linea rossa rappresenta l'andamento del portafoglio se avessi mantenuto i pesi attuali costanti nell'ultimo anno.")
