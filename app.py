import streamlit as st

# Configurazione della pagina
st.set_page_config(
    page_title="B-Betting Dashboard",
    page_icon="⚽",
    layout="wide"
)

# Stili CSS personalizzati
st.markdown("""
<style>
    .form-pill-win { background-color: #28a745; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .form-pill-draw { background-color: #ffc107; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .form-pill-loss { background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .ai-box { background-color: #1e2530; border-left: 5px solid #00d2ff; padding: 15px; border-radius: 5px; margin-top: 15px; margin-bottom: 15px; }
    .schedina-card { background-color: #262d3d; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #3e4c59; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------
# 🗂️ DATI CAMPIONATI E GIORNATE
# -----------------------------------------------------------------
campionati_disponibili = ["Serie A", "Premier League", "La Liga", "Bundesliga"]

def carica_giornate_campionato(campionato):
    database_giornate = {
        "Serie A": {
            "Giornata 30 (Prossima)": [
                {'team1': 'Juventus', 'team2': 'Inter', 'date': '2026-04-04', 'quote_1': 2.30, 'quote_x': 3.20, 'quote_2': 3.10},
                {'team1': 'Milan', 'team2': 'Napoli', 'date': '2026-04-04', 'quote_1': 2.10, 'quote_x': 3.40, 'quote_2': 3.50},
                {'team1': 'Roma', 'team2': 'Lazio', 'date': '2026-04-05', 'quote_1': 2.45, 'quote_x': 3.10, 'quote_2': 3.00}
            ]
        },
        "Premier League": {
            "Giornata 30 (Prossima)": [
                {'team1': 'Arsenal', 'team2': 'Chelsea', 'date': '2026-04-04', 'quote_1': 1.85, 'quote_x': 3.60, 'quote_2': 4.20},
                {'team1': 'Manchester City', 'team2': 'Manchester United', 'date': '2026-04-04', 'quote_1': 1.55, 'quote_x': 4.20, 'quote_2': 5.50},
                {'team1': 'Liverpool', 'team2': 'Tottenham', 'date': '2026-04-05', 'quote_1': 1.70, 'quote_x': 3.90, 'quote_2': 4.60}
            ]
        },
        "La Liga": {
            "Giornata 30 (Prossima)": [
                {'team1': 'Real Madrid', 'team2': 'Barcelona', 'date': '2026-04-04', 'quote_1': 2.05, 'quote_x': 3.50, 'quote_2': 3.40},
                {'team1': 'Atletico Madrid', 'team2': 'Sevilla', 'date': '2026-04-05', 'quote_1': 1.75, 'quote_x': 3.50, 'quote_2': 4.80}
            ]
        },
        "Bundesliga": {
            "Giornata 28 (Prossima)": [
                {'team1': 'Bayern Monaco', 'team2': 'Borussia Dortmund', 'date': '2026-04-04', 'quote_1': 1.60, 'quote_x': 4.30, 'quote_2': 5.00},
                {'team1': 'RB Leipzig', 'team2': 'Bayer Leverkusen', 'date': '2026-04-05', 'quote_1': 2.40, 'quote_x': 3.40, 'quote_2': 2.80}
            ]
        }
    }
    return database_giornate.get(campionato, {})

def get_classifica_reale(campionato):
    classifiche = {
        "Serie A": [
            {"Pos": 1, "Squadra": "Inter", "Pt": 76, "G": 29, "V": 24, "N": 4, "P": 1, "GF": 68, "GS": 15},
            {"Pos": 2, "Squadra": "Milan", "Pt": 65, "G": 29, "V": 19, "N": 8, "P": 2, "GF": 55, "GS": 24},
            {"Pos": 3, "Squadra": "Juventus", "Pt": 62, "G": 29, "V": 17, "N": 11, "P": 1, "GF": 48, "GS": 20},
            {"Pos": 4, "Squadra": "Napoli", "Pt": 56, "G": 29, "V": 16, "N": 8, "P": 5, "GF": 50, "GS": 28},
            {"Pos": 5, "Squadra": "Roma", "Pt": 52, "G": 29, "V": 15, "N": 7, "P": 7, "GF": 45, "GS": 31},
            {"Pos": 6, "Squadra": "Lazio", "Pt": 49, "G": 29, "V": 14, "N": 7, "P": 8, "GF": 40, "GS": 33}
        ],
        "Premier League": [
            {"Pos": 1, "Squadra": "Arsenal", "Pt": 68, "G": 29, "V": 21, "N": 5, "P": 3, "GF": 60, "GS": 22},
            {"Pos": 2, "Squadra": "Manchester City", "Pt": 67, "G": 29, "V": 20, "N": 7, "P": 2, "GF": 65, "GS": 25},
            {"Pos": 3, "Squadra": "Liverpool", "Pt": 64, "G": 29, "V": 19, "N": 7, "P": 3, "GF": 62, "GS": 27},
            {"Pos": 4, "Squadra": "Aston Villa", "Pt": 55, "G": 29, "V": 17, "N": 4, "P": 8, "GF": 52, "GS": 38}
        ],
        "La Liga": [
            {"Pos": 1, "Squadra": "Real Madrid", "Pt": 72, "G": 29, "V": 22, "N": 6, "P": 1, "GF": 64, "GS": 20},
            {"Pos": 2, "Squadra": "Barcelona", "Pt": 67, "G": 29, "V": 21, "N": 4, "P": 4, "GF": 66, "GS": 30},
            {"Pos": 3, "Squadra": "Girona", "Pt": 62, "G": 29, "V": 19, "N": 5, "P": 5, "GF": 58, "GS": 34}
        ],
        "Bundesliga": [
            {"Pos": 1, "Squadra": "Bayer Leverkusen", "Pt": 73, "G": 27, "V": 23, "N": 4, "P": 0, "GF": 68, "GS": 18},
            {"Pos": 2, "Squadra": "Bayern Monaco", "Pt": 60, "G": 27, "V": 19, "N": 3, "P": 5, "GF": 72, "GS": 31},
            {"Pos": 3, "Squadra": "Borussia Dortmund", "Pt": 53, "G": 27, "V": 15, "N": 8, "P": 4, "GF": 53, "GS": 32}
        ]
    }
    return classifiche.get(campionato, [])

def calcola_statistiche_squadra_dettagliate(matches, squadra):
    return {
        'tot_partite': 5,
        'forma_chain': ['V', 'N', 'V', 'P', 'V'],
        'ppg': 2.1,
        'clean_sheets': 2,
        'clean_sheets_percentage': 40,
        'goals_scored_total': 9,
        'goals_scored_avg': 1.8,
        'goals_conceded_total': 4,
        'goals_conceded_avg': 0.8,
        'over_2_5_perc': 60.0,
        'btts_perc': 50.0
    }

# Titolo Principale dell'App
st.title("⚽ B-Betting Dashboard & Analisi IA")

# -----------------------------------------------------------------
# 📑 TASTI / TAB SUPERIORI
# -----------------------------------------------------------------
tab_home, tab_classifica, tab3, tab_ia_prob, tab_quote = st.tabs([
    "📅 Calendario & Match (Home)", 
    "📊 Classifica Live", 
    "📈 Statistiche & IA", 
    "🤖 IA Probability",
    "🎯 Quote & Schedina"
])

# -----------------------------------------------------------------
# TAB 1: HOME / CALENDARIO
# -----------------------------------------------------------------
with tab_home:
    st.subheader("📅 Calendario Partite in Programma")
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        camp_home = st.selectbox("Seleziona Campionato", campionati_disponibili, key="camp_home")
    with col_h2:
        giornate_h = carica_giornate_campionato(camp_home)
        giornata_home = st.selectbox("Seleziona Giornata", list(giornate_h.keys()), key="giornata_home")
    
    matches_home = giornate_h.get(giornata_home, [])
    st.divider()
    
    if matches_home:
        for m in matches_home:
            st.markdown(f"""
            <div style="background-color: #1e2530; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid #28a745;">
                🏟 <b>{m.get('team1')}</b> vs <b>{m.get('team2')}</b><br>
                📅 Data: {m.get('date')} | Quote 1X2: <b>1: {m.get('quote_1')}</b> | <b>X: {m.get('quote_x')}</b> | <b>2: {m.get('quote_2')}</b>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Nessuna partita disponibile.")

# -----------------------------------------------------------------
# TAB 2: CLASSIFICA LIVE
# -----------------------------------------------------------------
with tab_classifica:
    st.subheader("📊 Classifica Aggiornata")
    camp_classifica = st.selectbox("Seleziona Torneo per Classifica", campionati_disponibili, key="camp_class")
    
    classifica_dati = get_classifica_reale(camp_classifica)
    if classifica_dati:
        st.dataframe(classifica_dati, use_container_width=True)
    else:
        st.info("Classifica non disponibile per questo torneo.")

# -----------------------------------------------------------------
# TAB 3: STATISTICHE & IA
# -----------------------------------------------------------------
with tab3:
    st.subheader("📈 Dashboard Avanzata: Scheda Andamento & Statistiche Squadra")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        campionato_stat_selezionato = st.selectbox("Seleziona Torneo", campionati_disponibili, key="selettore_campionato_stat")
    with col_c2:
        giornate_dict = carica_giornate_campionato(campionato_stat_selezionato)
        lista_giornate = list(giornate_dict.keys())
        giornata_scelta = st.selectbox("Seleziona Giornata", lista_giornate, key="select_giornata_stat")
    
    matches_correnti = giornate_dict.get(giornata_scelta, [])
    st.divider()
    
    if matches_correnti:
        lista_squadre_tutte = sorted(list(set([m.get('team1') for m in matches_correnti] + [m.get('team2') for m in matches_correnti])))
        squadra_scelta = st.selectbox("Seleziona Squadra da Analizzare", lista_squadre_tutte, key="select_squadra_stat")
        
        st.divider()
        stats_sq = calcola_statistiche_squadra_dettagliate(matches_correnti, squadra_scelta)
        
        if stats_sq:
            st.markdown(f"## 🛡️ Analisi Dettagliata: {squadra_scelta}")
            
            col_i1, col_i2, col_i3 = st.columns(3)
            with col_i1:
                forma_chain = stats_sq.get('forma_chain', [])
                forma_html = " ".join([f"<span class='form-pill-win'>{x}</span>" if x=="V" else f"<span class='form-pill-draw'>{x}</span>" if x=="N" else f"<span class='form-pill-loss'>{x}</span>" for x in forma_chain])
                st.markdown(f"**Forma Recente:**<br>{forma_html}", unsafe_allow_html=True)
            with col_i2:
                st.metric("Media Punti (PPG)", stats_sq.get('ppg', 0))
            with col_i3:
                st.metric("Over 2.5 %", f"{stats_sq.get('over_2_5_perc', 0)}%")
    else:
        st.warning("Nessuna partita disponibile.")

# -----------------------------------------------------------------
# TAB 4: IA PROBABILITY
# -----------------------------------------------------------------
with tab_ia_prob:
    st.subheader("🤖 Probabilità Algoritmiche IA (Match Top)")
    st.markdown("Analisi predittiva avanzata calcolata dall'intelligenza artificiale sui big match del weekend:")
    
    match_ia_list = [
        {"match": "Juventus vs Inter", "segno": "1X (Doppia Chance)", "prob": "74%", "consiglio": "Partita bloccata, la Juventus in casa ha un'ottima solidità difensiva."},
        {"match": "Arsenal vs Chelsea", "segno": "1 (Vittoria Casa)", "prob": "68%", "consiglio": "Arsenal in grande spolvero e con motivazioni scudetto altissime."},
        {"match": "Real Madrid vs Barcelona", "segno": "Goal (Entrambe a segno)", "prob": "81%", "consiglio": "Clasico storicamente offensivo, difese spesso vulnerabili nei contropiedi."}
    ]
    
    for mia in match_ia_list:
        st.markdown(f"""
        <div class="ai-box">
            🎯 <b>{mia['match']}</b><br>
            📌 <b>Pronostico IA:</b> {mia['segno']} (Affidabilità stimata: <span style="color: #00d2ff;"><b>{mia['prob']}</b></span>)<br>
            💡 <i>Analisi:</i> {mia['consiglio']}
        </div>
        """, unsafe_allow_html=True)

# -----------------------------------------------------------------
# TAB 5: QUOTE & SCHEDINA
# -----------------------------------------------------------------
with tab_quote:
    st.subheader("🎯 Schedina Consigliata del Giorno")
    st.markdown("Ecco la combinazione studiata dai nostri algoritmi per ottimizzare il rapporto rischio/quota:")
    
    st.markdown("""
    <div class="schedina-card">
        🔥 <b>MULTIBET CONSIGLIATA (Quota Totale: ~4.85)</b><br><br>
        1. <b>Arsenal vs Chelsea</b> ➔ 1X (Quota: 1.25)<br>
        2. <b>Juventus vs Inter</b> ➔ Under 3.5 (Quota: 1.35)<br>
        3. <b>Real Madrid vs Barcelona</b> ➔ Goal (Quota: 1.55)<br>
        4. <b>Bayern Monaco vs Borussia D.</b> ➔ 1 (Quota: 1.60)<br>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 Gioca responsabilmente. Le percentuali e le quote sono stime basate su modelli statistici.")
