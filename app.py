import streamlit as st

# Configurazione della pagina
st.set_page_config(
    page_title="B-Betting Dashboard",
    page_icon="⚽",
    layout="wide"
)

# Iniezione stili CSS
st.markdown("""
<style>
    .form-pill-win { background-color: #28a745; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .form-pill-draw { background-color: #ffc107; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .form-pill-loss { background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .ai-box { background-color: #1e2530; border-left: 5px solid #00d2ff; padding: 15px; border-radius: 5px; margin-top: 15px; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------
# 🗂️ DATABASE CAMPIONATI E GIORNATE
# -----------------------------------------------------------------
campionati_disponibili = ["Serie A", "Premier League", "La Liga", "Bundesliga"]

def carica_giornate_campionato(campionato):
    database_giornate = {
        "Serie A": {
            "Giornata 30 (Prossima)": [
                {'team1': 'Juventus', 'team2': 'Inter', 'date': '2026-04-04'},
                {'team1': 'Milan', 'team2': 'Napoli', 'date': '2026-04-04'},
                {'team1': 'Roma', 'team2': 'Lazio', 'date': '2026-04-05'}
            ],
            "Giornata 31": [
                {'team1': 'Atalanta', 'team2': 'Fiorentina', 'date': '2026-04-11'},
                {'team1': 'Bologna', 'team2': 'Torino', 'date': '2026-04-11'}
            ]
        },
        "Premier League": {
            "Giornata 30 (Prossima)": [
                {'team1': 'Arsenal', 'team2': 'Chelsea', 'date': '2026-04-04'},
                {'team1': 'Manchester City', 'team2': 'Manchester United', 'date': '2026-04-04'},
                {'team1': 'Liverpool', 'team2': 'Tottenham', 'date': '2026-04-05'}
            ]
        },
        "La Liga": {
            "Giornata 30 (Prossima)": [
                {'team1': 'Real Madrid', 'team2': 'Barcelona', 'date': '2026-04-04'},
                {'team1': 'Atletico Madrid', 'team2': 'Sevilla', 'date': '2026-04-05'}
            ]
        },
        "Bundesliga": {
            "Giornata 28 (Prossima)": [
                {'team1': 'Bayern Monaco', 'team2': 'Borussia Dortmund', 'date': '2026-04-04'},
                {'team1': 'RB Leipzig', 'team2': 'Bayer Leverkusen', 'date': '2026-04-05'}
            ]
        }
    }
    return database_giornate.get(campionato, {"Prossima Giornata": []})

def calcola_statistiche_squadra_dettagliate(matches, squadra, sede, trend):
    return {
        'tot_partite': 5,
        'forma_chain': ['V', 'N', 'V', 'P', 'V'],
        'ppg': 2.1,
        'clean_sheets': 2,
        'clean_sheets_percentage': 40,
        'goals_scored_total': 9,
        'goals_scored_avg': 1.8,
        'shots_total_avg': 14.5,
        'shots_on_target_avg': 5.2,
        'goals_conceded_total': 4,
        'goals_conceded_avg': 0.8,
        'shots_conceded_avg': 10.1,
        'shots_on_target_conceded_avg': 3.2,
        'over_1_5_perc': 80.0,
        'over_2_5_perc': 60.0,
        'btts_perc': 50.0
    }

st.title("⚽ B-Betting Dashboard & Analisi IA")

tab_home, tab_classifica, tab3, tab_ia_prob, tab_quote = st.tabs([
    "📅 Calendario & Match (Home)", 
    "📊 Classifica Live", 
    "📈 Statistiche & IA", 
    "🤖 IA Probability",
    "🎯 Quote & Schedina"
])

with tab_home:
    st.subheader("📅 Calendario Partite")
    st.write("Benvenuto nella dashboard principale di B-Betting.")

with tab_classifica:
    st.subheader("📊 Classifica Aggiornata")
    st.write("Sezione classifiche in aggiornamento.")

# -----------------------------------------------------------------
# TAB 3: STATISTICHE & H2H (CON SELEZIONE CAMPIONATO E GIORNATA CHIARA)
# -----------------------------------------------------------------
with tab3:
    st.subheader("📈 Dashboard Avanzata & Analisi H2H")
    
    # Pannello di controllo unificato in alto
    st.markdown("### ⚙️ Filtri di Selezione")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        campionato_stat_selezionato = st.selectbox(
            "1️⃣ Seleziona Campionato:", 
            campionati_disponibili, 
            index=0, 
            key="selettore_campionato_stat"
        )
    with col_c2:
        giornate_dict = carica_giornate_campionato(campionato_stat_selezionato)
        lista_giornate = list(giornate_dict.keys())
        giornata_scelta = st.selectbox("2️⃣ Seleziona Giornata:", lista_giornate, key="select_giornata")
    
    matches_correnti = giornate_dict.get(giornata_scelta, [])
    
    st.divider()
    
    if matches_correnti:
        # Sezione Analisi Squadra Singola
        lista_squadre_tutte = sorted(list(set([m.get('team1') for m in matches_correnti] + [m.get('team2') for m in matches_correnti])))
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            squadra_scelta = st.selectbox("Seleziona Squadra da Analizzare", lista_squadre_tutte)
        with col_f2:
            trend_short = st.selectbox("Trend Short-term", ["Tutte", "Ultime 5", "Ultime 10"])
        
        st.divider()
        
        stats_sq = calcola_statistiche_squadra_dettagliate(matches_correnti, squadra_scelta, "Tutte le Partite", trend_short)
        
        if stats_sq:
            st.markdown(f"## 🛡️ Analisi: {squadra_scelta}")
            col_i1, col_i2, col_i3 = st.columns(3)
            with col_i1:
                forma_chain = stats_sq.get('forma_chain', [])
                forma_html = " ".join([f"<span class='form-pill-win'>{x}</span>" if x=="V" else f"<span class='form-pill-draw'>{x}</span>" if x=="N" else f"<span class='form-pill-loss'>{x}</span>" for x in forma_chain])
                st.markdown(f"**Forma Recente:**<br>{forma_html}", unsafe_allow_html=True)
            with col_i2:
                st.metric("Media Punti (PPG)", stats_sq.get('ppg', 0))
            with col_i3:
                st.metric("Over 2.5 %", f"{stats_sq.get('over_2_5_perc', 0)}%")
        
        # SEZIONE H2H
        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown(f"### ⚔️ Confronti Diretti (H2H) - {campionato_stat_selezionato} ({giornata_scelta})")
        
        opzioni_h2h = [f"{m.get('team1')} vs {m.get('team2')} ({m.get('date', 'N/D')})" for m in matches_correnti]
        scelta_match_h2h = st.selectbox("Seleziona la partita in programma:", opzioni_h2h, key="select_match_h2h_tab3")
        
        if scelta_match_h2h:
            idx_h2h = opzioni_h2h.index(scelta_match_h2h)
            m_h2h = matches_correnti[idx_h2h]
            s1, s2 = m_h2h.get('team1'), m_h2h.get('team2')
            
            st.markdown(f"#### 🏟 Match: **{s1}** vs **{s2}**")
            col_h1, col_h_vs, col_h2 = st.columns([0.45, 0.1, 0.45])
            with col_h1:
                st.markdown(f"**{s1}**")
                st.metric("PPG", "2.1")
            with col_h_vs:
                st.markdown("<div style='text-align: center; padding-top: 30px; font-weight: bold;'>VS</div>", unsafe_allow_html=True)
            with col_h2:
                st.markdown(f"**{s2}**")
                st.metric("PPG", "1.9")
    else:
        st.warning("Nessuna partita trovata per questa combinazione.")

with tab_ia_prob:
    st.subheader("🤖 Probabilità Algoritmiche IA")
    st.write("In aggiornamento.")

with tab_quote:
    st.subheader("🎯 Quote & Schedina Consigliata")
    st.write("In aggiornamento.")
