import streamlit as st

# Configurazione della pagina (deve essere la prima istruzione Streamlit)
st.set_page_config(
    page_title="Bomba Betting Live",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile CSS personalizzato per dare un look ultra-professionale ed elegante
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
    </style>
""", unsafe_allow_html=True)

# Header Principale
st.title("⚽ Bomba Betting — Live Dashboard")
st.markdown("##### *Architettura dati reali in tempo reale*")
st.divider()

# Barra laterale di navigazione
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/football2--v1.png", width=70)
    st.header("Pannello di Controllo")
    
    # Selezione campionato
    campionato = st.selectbox(
        "Seleziona Torneo",
        ["Serie A", "Premier League", "La Liga", "Bundesliga", "Champions League"]
    )
    
    st.divider()
    
    # Stato del sistema (Trasparenza al 100%)
    st.markdown("**Stato Connessione:**")
    st.success("🟢 Sistema pronto per lo scraping live")
    
    if st.button("Aggiorna Dati Rete"):
        st.toast("Interrogazione in corso...", icon="🔄")

# Sezione di Ricerca Principale con Lente (stile elegante affiancato)
col_search_icon, col_search_input = st.columns([0.05, 0.95])
with col_search_icon:
    st.markdown("### 🔍")
with col_search_input:
    ricerca = st.text_input("", placeholder="Cerca squadra, giocatore o match...", label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

# Layout a schede per dare un impatto visivo ordinato
tab1, tab2, tab3 = st.tabs(["📊 Classifica Live", "📅 Calendario", "📈 Statistiche"])

with tab1:
    st.subheader(f"Classifica Ufficiale - {campionato}")
    st.info("💡 Qui apparirà la tabella estratta in tempo reale dalle fonti aperte della rete. Nessun dato fittizio.")
    
    # Esempio visivo pulito di struttura tabella vuota pronta a ricevere i dati reali
    st.markdown("""
        <div class="metric-card">
            <p style="text-align: center; color: #8b949e; margin: 0;">In attesa di attivare il modulo di scraping per popolare la tabella di %s...</p>
        </div>
    """ % campionato, unsafe_allow_html=True)

with tab2:
    st.subheader("Prossimi Incontri")
    st.write("Il calendario aggiornato giornata per giornata comparirà qui.")

with tab3:
    st.subheader("Analisi Avanzata")
    st.write("Metriche di rendimento basate sui gol reali.")

# Footer di classe
st.markdown("<br><hr><p style='text-align: center; color: #8b949e; font-size: 12px;'>Bomba Betting Dashboard — Progettato per dati reali.</p>", unsafe_allow_html=True)
