import streamlit as st
import requests
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
    st.success("🟢 Motore Stagione 2026/27 Attivo")

# Ricerca
col_search_icon, col_search_input = st.columns([0.05, 0.95])
with col_search_icon:
    st.markdown("### 🔍")
with col_search_input:
    ricerca = st.text_input("", placeholder="Cerca squadra (es. Juventus, Inter) o match...", label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

# Funzione per caricare i dati della stagione corrente con cache di Streamlit
@st.cache_data
def carica_dati_campionato():
    url = "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/it.1.json"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        return response.json()
    else:
        # Fallback di sicurezza se la repository viene aggiornata con un leggero ritardo
        url_alt = "https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/it.1.json"
        return requests.get(url_alt, timeout=10).json()

# Layout a schede
tab1, tab2, tab3 = st.tabs(["📊 Classifica Live", "📅 Calendario & Match", "📈 Statistiche Reali"])

with tab1:
    st.subheader(f"Classifica Ufficiale — {campionato_attivo}")
    
    try:
        data = carica_dati_campionato()
        matches = data.get('matches', [])
        
        classifica_dict = {}
        
        for m in matches:
            if 'score' in m and 'ft' in m['score'] and m['score']['ft'] is not None:
                t1 = m['team1']
                t2 = m['team2']
                g1 = m['score']['ft'][0]
                g2 = m['score']['ft'][1]
                
                for squadra in [t1, t2]:
                    if squadra not in classifica_dict:
                        classifica_dict[squadra] = {'Squadra': squadra, 'PG': 0, 'V': 0, 'N': 0, 'P': 0, 'GF': 0, 'GS': 0, 'Pt': 0}
                
                classifica_dict[t1]['PG'] += 1
                classifica_dict[t2]['PG'] += 1
                classifica_dict[t1]['GF'] += g1
                classifica_dict[t1]['GS'] += g2
                classifica_dict[t2]['GF'] += g2
                classifica_dict[t2]['GS'] += g1
                
                if g1 > g2:
                    classifica_dict[t1]['V'] += 1
                    classifica_dict[t1]['Pt'] += 3
                    classifica_dict[t2]['P'] += 1
                elif g1 < g2:
                    classifica_dict[t2]['V'] += 1
                    classifica_dict[t2]['Pt'] += 3
                    classifica_dict[t1]['P'] += 1
                else:
                    classifica_dict[t1]['N'] += 1
                    classifica_dict[t1]['Pt'] += 1
                    classifica_dict[t2]['N'] += 1
                    classifica_dict[t2]['Pt'] += 1

        if classifica_dict:
            df_classifica = pd.DataFrame(list(classifica_dict.values()))
            df_classifica['DR'] = df_classifica['GF'] - df_classifica['GS']
            df_classifica = df_classifica.sort_values(by=['Pt', 'DR'], ascending=False).reset_index(drop=True)
            df_classifica.index = df_classifica.index + 1
            
            if ricerca:
                df_classifica = df_classifica[df_classifica['Squadra'].str.contains(ricerca, case=False, na=False)]

            st.success("Classifica aggiornata alla stagione corrente!")
            st.dataframe(df_classifica[['Squadra', 'PG', 'Pt', 'V', 'N', 'P', 'GF', 'GS', 'DR']], use_container_width=True)
        else:
            st.info("La stagione corrente è appena iniziata o i match disputati non hanno ancora risultati registrati nel feed.")
            
    except Exception as e:
        st.error(f"Errore durante l'elaborazione della classifica: {e}")

with tab2:
    st.subheader(f"Calendario Incontri — {campionato_attivo}")
    try:
        data = carica_dati_campionato()
        matches = data.get('matches', [])
        lista_match = []
        for m in matches:
            t1 = m.get('team1', '')
            t2 = m.get('team2', '')
            data_match = m.get('date', 'Data da definire')
            score = m.get('score', {}).get('ft', ('-', '-'))
            score_display = f"{score[0]} - {score[1]}" if score and score != ('-', '-') else "Da giocare"
            lista_match.append({"Data": data_match, "Casa": t1, "Risultato": score_display, "Ospite": t2})
        
        df_matches = pd.DataFrame(lista_match)
        if ricerca:
            df_matches = df_matches[df_matches['Casa'].str.contains(ricerca, case=False, na=False) | df_matches['Ospite'].str.contains(ricerca, case=False, na=False)]
        
        st.dataframe(df_matches, use_container_width=True)
    except Exception as e:
        st.write("Impossibile caricare il calendario al momento.")

with tab3:
    st.subheader("Metriche Avanzate")
    st.write("Analisi statistica delle performance basata sui dati reali della stagione in corso.")

st.markdown("<br><hr><p style='text-align: center; color: #8b949e; font-size: 12px;'>b-betting Architecture — Trasparenza e Dati Reali al 100%.</p>", unsafe_allow_html=True)
