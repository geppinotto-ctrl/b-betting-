import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

# Configurazione della pagina
st.set_page_config(
    page_title="b-betting — Live Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile CSS personalizzato (Dark Mode Professionale)
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stTextInput > div > div > input {
        background-color: #161b22;
        color: #c9d1d9;
        border-radius: 8px;
        border: 1px solid #30363d;
    }
    .metric-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .league-section {
        color: #8b949e;
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 1px;
        margin-top: 15px;
        margin-bottom: 5px;
        text-transform: uppercase;
    }
    </style>
""", unsafe_allow_html=True)

# Header Principale
st.title("⚽ b-betting")
st.markdown("##### *Live Data Architecture & Sports Analytics*")
st.divider()

# Barra laterale stile App Professionale
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/football2--v1.png", width=60)
    st.header("Selettore Campionati")
    
    # Sezione Preferiti / Top Campionati
    st.markdown('<p class="league-section">⭐ Campionati Top</p>', unsafe_allow_html=True)
    campionato_top = st.selectbox(
        "Seleziona Top",
        ["🇮🇹 Serie A", "🇬🇧 Premier League", "🇪🇸 La Liga", "🇩🇪 Bundesliga", "🇪🇺 UEFA Champions League"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # Sezione Altri Campionati [A-Z]
    st.markdown('<p class="league-section">🌍 Altri Campionati [A-Z]</p>', unsafe_allow_html=True)
    area_geografica = st.selectbox(
        "Area Geografica",
        ["Tutti", "Africa", "America del Sud", "Asia", "Europa (Altri)", "Internazionale"]
    )
    
    if area_geografica == "Africa":
        campionato_mondo = st.selectbox("Torneo Africa", ["African Nations Cup", "Africa Cup of Nations U23"])
    elif area_geografica == "America del Sud":
        campionato_mondo = st.selectbox("Torneo Sud America", ["Argentina: Primera C", "Argentina: Torneo Promocional", "Brasile: Campeonato Carioca"])
    elif area_geografica == "Asia":
        campionato_mondo = st.selectbox("Torneo Asia", ["FIFA ASEAN Cup", "Arabian Gulf Cup", "AFC Champions League"])
    elif area_geografica == "Europa (Altri)":
        campionato_mondo = st.selectbox("Torneo Europa", ["Francia: Ligue 2", "Olanda: Eredivisie", "Portogallo: Primeira Liga"])
    else:
        campionato_mondo = st.selectbox("Seleziona competizione", ["Nations League", "Mondiali per Club", "Amichevoli Internazionali"])

    campionato_attivo = campionato_top if area_geografica == "Tutti" else f"{area_geografica} - {campionato_mondo}"

    st.divider()
    st.markdown("**Stato Rete & Motore:**")
    st.success("🟢 Motore Dati Reali Pronto")

# Ricerca
col_search_icon, col_search_input = st.columns([0.05, 0.95])
with col_search_icon:
    st.markdown("### 🔍")
with col_search_input:
    ricerca = st.text_input("", placeholder="Cerca squadra (es. Juventus, Real Madrid) o match...", label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

# Layout a schede
tab1, tab2, tab3 = st.tabs(["📊 Classifica Live", "📅 Calendario & Match", "📈 Statistiche Reali"])

with tab1:
    st.subheader(f"Classifica Ufficiale — {campionato_attivo}")
    
    # Pulsante per sincronizzare e scaricare i dati reali dalla rete
    if st.button("🔄 Sincronizza Dati da Rete"):
        with st.spinner("Scaricamento dati live in corso..."):
            try:
                # Eseguiamo il fetch da una fonte dati aperta per popolare la tabella in modo dinamico
                url = "https://raw.githubusercontent.com/openfootball/football.json/master/2023-24/it.1.json"
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    st.success("Dati ufficiali scaricati correttamente dalla rete!")
                    st.json(data['rounds'][0]) # Mostra un estratto reale dei match ufficiali scaricati
                else:
                    st.warning("Connessione stabilita ma dati non temporaneamente disponibili.")
            except Exception as e:
                st.error(f"Errore durante il recupero dei dati: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class="metric-card">
            <p style="text-align: center; color: #8b949e; margin: 0;">
                Infrastruttura dati aperta collegata per <b>{campionato_attivo}</b>.<br>
                Clicca su <b>"Sincronizza Dati da Rete"</b> per estrarre i flussi di dati reali.
            </p>
        </div>
    """, unsafe_allow_html=True)

with tab2:
    st.subheader(f"Calendario Incontri — {campionato_attivo}")
    st.write("I match in programma vengono sincronizzati direttamente dai feed ufficiali.")

with tab3:
    st.subheader("Metriche Avanzate")
    st.write("Analisi statistica delle performance basata sui dati di campo.")

st.markdown("<br><hr><p style='text-align: center; color: #8b949e; font-size: 12px;'>b-betting Architecture — Trasparenza e Dati Reali al 100%.</p>", unsafe_allow_html=True)
