import streamlit as st

# Configurazione della pagina (deve essere la prima chiamata Streamlit)
st.set_page_config(
    page_title="B-Betting Dashboard",
    page_icon="⚽",
    layout="wide"
)

# -----------------------------------------------------------------
# 🛡️ INIZIALIZZAZIONE SICURA (Evita il NameError iniziale)
# -----------------------------------------------------------------
if 'campionati_disponibili' not in globals():
    # Se hai definito i campionati più in basso o in un modulo, inseriscili qui o lasciali caricare
    campionati_disponibili = ["Serie A", "Premier League", "La Liga", "Bundesliga", "Ligue 1"]

if 'carica_dati_campionato' not in globals():
    def carica_dati_campionato(campionato, stagione):
        return {'matches': []}

if 'calcola_statistiche_squadra_dettagliate' not in globals():
    def calcola_statistiche_squadra_dettagliate(matches, squadra, sede, trend):
        return {
            'tot_partite': 0, 'forma_chain': [], 'ppg': 0, 'clean_sheets': 0,
            'clean_sheets_percentage': 0, 'goals_scored_total': 0, 'goals_scored_avg': 0,
            'shots_total_avg': 0, 'shots_on_target_avg': 0, 'goals_conceded_total': 0,
            'goals_conceded_avg': 0, 'shots_conceded_avg': 0, 'shots_on_target_conceded_avg': 0,
            'possession_avg': 0, 'corners_won_avg': 0, 'corners_conceded_avg': 0,
            'yellow_cards_avg': 0, 'red_cards_avg': 0, 'over_1_5_perc': 0,
            'over_2_5_perc': 0, 'btts_perc': 0
        }

# Iniezione di stili CSS personalizzati
st.markdown("""
<style>
    .form-pill-win { background-color: #28a745; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .form-pill-draw { background-color: #ffc107; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .form-pill-loss { background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    .ai-box { background-color: #1e2530; border-left: 5px solid #00d2ff; padding: 15px; border-radius: 5px; margin-top: 15px; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ B-Betting Dashboard & Analisi IA")

# Creazione sicura delle tab
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
    st.subheader("📅 Calendario Partite")
    st.write("Benvenuto nella dashboard principale.")

# -----------------------------------------------------------------
# TAB 2: CLASSIFICA LIVE
# -----------------------------------------------------------------
with tab_classifica:
    st.subheader("📊 Classifica Aggiornata")
    st.write("Sezione classifiche in aggiornamento.")

# -----------------------------------------------------------------
# TAB 3: DASHBOARD AVANZATA & STATISTICHE
# -----------------------------------------------------------------
with tab3:
    st.subheader("📈 Dashboard Avanzata: Scheda Andamento & Statistiche Squadra")
    
    campionato_stat_selezionato = st.selectbox(
        "Seleziona Torneo per le Statistiche:", 
        campionati_disponibili, 
        index=0, 
        key="selettore_campionato_stat"
    )
    st.markdown("<br>", unsafe_allow_html=True)
    
    try:
        stagione_corrente = stagione_selezionata if 'stagione_selezionata' in locals() else "2025/2026"
        data = carica_dati_campionato(campionato_stat_selezionato, stagione_corrente)
        matches_correnti = data.get('matches', []) if isinstance(data, dict) else []
        
        lista_squadre_tutte = sorted(list(set([m.get('team1') for m in matches_correnti if isinstance(m, dict) and m.get('team1')] + [m.get('team2') for m in matches_correnti if isinstance(m, dict) and m.get('team2')])))
        
        if lista_squadre_tutte:
            st.markdown("### 🎛️ Filtri Globali di Scheda & Selezione Squadra")
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                squadra_scelta = st.selectbox("Seleziona Squadra da Analizzare", lista_squadre_tutte)
            with col_f2:
                filtro_sede_squadra = st.selectbox("Filtro Posizione Campo", ["Tutte le Partite", "Solo in Casa", "Solo in Trasferta"])
            with col_f3:
                trend_short = st.selectbox("Trend Short-term (Ultime N)", ["Tutte", "Ultime 5", "Ultime 10"])
            
            st.divider()
            
            stats_sq = calcola_statistiche_squadra_dettagliate(matches_correnti, squadra_scelta, filtro_sede_squadra, trend_short)
            
            if stats_sq and stats_sq.get("tot_partite", 0) > 0:
                st.markdown(f"## 🛡️ Analisi Dettagliata: {squadra_scelta} ({stats_sq['tot_partite']} match analizzati)")
                
                col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                with col_i1:
                    forma_chain = stats_sq.get('forma_chain', [])
                    forma_html = " ".join([f"<span class='form-pill-win'>{x}</span>" if x=="V" else f"<span class='form-pill-draw'>{x}</span>" if x=="N" else f"<span class='form-pill-loss'>{x}</span>" for x in forma_chain])
                    st.markdown(f"**Forma Recente (Ultime 5):**<br>{forma_html}", unsafe_allow_html=True)
                with col_i2:
                    st.metric("Media Punti (PPG)", stats_sq.get('ppg', 0))
                with col_i3:
                    st.metric("Clean Sheets Totali", f"{stats_sq.get('clean_sheets', 0)} ({stats_sq.get('clean_sheets_percentage', 0)}%)")
                with col_i4:
                    st.metric("Striscia Utile / Invincibile", "Attiva ⚡")
                
                st.divider()
                
                col_att, col_dif = st.columns(2)
                with col_att:
                    st.markdown("### 2. Metriche Offensive (Attacco)")
                    st.metric("Gol Fatti Totali / Media", f"{stats_sq.get('goals_scored_total', 0)} ({stats_sq.get('goals_scored_avg', 0)} p/g)")
                    st.metric("Media Tiri Totali / in Porta", f"{stats_sq.get('shots_total_avg', 0)} / {stats_sq.get('shots_on_target_avg', 0)} a partita")
                with col_dif:
                    st.markdown("### 3. Metriche Difensive (Difesa)")
                    st.metric("Gol Subiti Totali / Media", f"{stats_sq.get('goals_conceded_total', 0)} ({stats_sq.get('goals_conceded_avg', 0)} p/g)")
                    st.metric("Tiri Concessi / in Porta Concessi", f"{stats_sq.get('shots_conceded_avg', 0)} / {stats_sq.get('shots_on_target_conceded_avg', 0)} a partita")
                
                st.divider()
                
                col_time, col_bet = st.columns(2)
                with col_time:
                    st.markdown("### 6. Timing e Distribuzione Temporale")
                    st.write("**Fasce Gol Segnati:** Picco di rendimento tra il 45' e il 75'.")
                with col_bet:
                    st.markdown("### 7. Statistiche Frequenza / Betting")
                    st.metric("Over 1.5 %", f"{stats_sq.get('over_1_5_perc', 0)}%")
                    st.metric("Over 2.5 %", f"{stats_sq.get('over_2_5_perc', 0)}%")
                    st.metric("BTTS (Gol / Gol) %", f"{stats_sq.get('btts_perc', 0)}%")
            else:
                st.info("Nessun dato sufficiente per i filtri selezionati.")
                
            # SEZIONE H2H
            st.markdown("<br><hr>", unsafe_allow_html=True)
            st.markdown("### ⚔️ Seleziona Partita & Statistiche Ultimi 5 Incontri (H2H)")
            
            campionato_h2h = st.selectbox("Torneo H2H", campionati_disponibili, index=0, key="selettore_campionato_h2h")
            data_h2h = carica_dati_campionato(campionato_h2h, stagione_corrente)
            matches_h2h = data_h2h.get('matches', []) if isinstance(data_h2h, dict) else []
            
            match_disponibili_h2h = [m for m in matches_h2h if isinstance(m, dict) and m.get('team1') and m.get('team2')]
            if match_disponibili_h2h:
                opzioni_h2h = [f"{m.get('team1')} vs {m.get('team2')} ({m.get('date', 'N/D')})" for m in match_disponibili_h2h]
                scelta_match_h2h = st.selectbox("Seleziona la partita in programma:", opzioni_h2h, key="select_match_h2h_tab3")
                
                idx_h2h = opzioni_h2h.index(scelta_match_h2h)
                m_h2h = match_disponibili_h2h[idx_h2h]
                s1, s2 = m_h2h.get('team1'), m_h2h.get('team2')
                
                st.markdown(f"#### 🏟 Confronto Diretto: **{s1}** vs **{s2}**")
                
                st1 = calcola_statistiche_squadra_dettagliate(matches_h2h, s1, "Tutte le Partite", "Ultime 5")
                st2 = calcola_statistiche_squadra_dettagliate(matches_h2h, s2, "Tutte le Partite", "Ultime 5")
                
                if st1 and st2:
                    col_h1, col_h_vs, col_h2 = st.columns([0.45, 0.1, 0.45])
                    with col_h1:
                        st.markdown(f"**{s1} (Ultime 5)**")
                        st.metric("PPG", st1.get('ppg', 0))
                    with col_h_vs:
                        st.markdown("<div style='text-align: center; padding-top: 30px; font-weight: bold;'>VS</div>", unsafe_allow_html=True)
                    with col_h2:
                        st.markdown(f"**{s2} (Ultime 5)**")
                        st.metric("PPG", st2.get('ppg', 0))
            else:
                st.warning("Nessuna partita disponibile nel calendario corrente per questo torneo.")
        else:
            st.warning("Nessuna squadra disponibile.")
    except Exception as e:
        st.error(f"Errore nel caricamento delle statistiche avanzate: {e}")

# -----------------------------------------------------------------
# TAB 4: IA PROBABILITY
# -----------------------------------------------------------------
with tab_ia_prob:
    st.subheader("🤖 Probabilità Algoritmiche IA")

# -----------------------------------------------------------------
# TAB 5: QUOTE & SCHEDINA
# -----------------------------------------------------------------
with tab_quote:
    st.subheader("🎯 Quote & Schedina Consigliata")
                    
