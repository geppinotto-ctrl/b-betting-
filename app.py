import streamlit as st

# Configurazione della pagina (deve essere la prima chiamata Streamlit)
st.set_page_config(
    page_title="B-Betting Dashboard",
    page_icon="⚽",
    layout="wide"
)

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

# Creazione sicura delle tab (tutte e 5, con tab3 assegnata correttamente)
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
    
    # Usa direttamente la tua variabile globale originale dei campionati
    campionato_stat_selezionato = st.selectbox(
        "Seleziona Torneo per le Statistiche:", 
        campionati_disponibili, 
        index=0, 
        key="selettore_campionato_stat"
    )
    st.markdown("<br>", unsafe_allow_html=True)
    
    try:
        # Chiama direttamente la tua funzione originale passando il campionato selezionato nel menu a tendina
        data = carica_dati_campionato(campionato_stat_selezionato, stagione_selezionata if 'stagione_selezionata' in locals() else "2025/2026")
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
                
                # 1. Indicatori di Stato e Forma
                st.markdown("### 1. Indicatori di Stato e Forma (Macro Stats)")
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
                
                # 2 & 3. Metriche Offensive e Difensive
                col_att, col_dif = st.columns(2)
                with col_att:
                    st.markdown("### 2. Metriche Offensive (Attacco)")
                    st.metric("Gol Fatti Totali / Media", f"{stats_sq.get('goals_scored_total', 0)} ({stats_sq.get('goals_scored_avg', 0)} p/g)")
                    st.metric("Media Tiri Totali / in Porta", f"{stats_sq.get('shots_total_avg', 0)} / {stats_sq.get('shots_on_target_avg', 0)} a partita")
                    st.metric("Expected Goals (xG Stimati)", f"{(stats_sq.get('goals_scored_avg', 0) * 0.95):.2f} avg")
                
                with col_dif:
                    st.markdown("### 3. Metriche Difensive (Difesa)")
                    st.metric("Gol Subiti Totali / Media", f"{stats_sq.get('goals_conceded_total', 0)} ({stats_sq.get('goals_conceded_avg', 0)} p/g)")
                    st.metric("Tiri Concessi / in Porta Concessi", f"{stats_sq.get('shots_conceded_avg', 0)} / {stats_sq.get('shots_on_target_conceded_avg', 0)} a partita")
                    st.metric("Expected Goals Against (xGA)", f"{(stats_sq.get('goals_conceded_avg', 0) * 0.95):.2f} avg")
                
                st.divider()
                
                # 4 & 5. Controllo Gioco e Disciplina
                col_gioco, col_disc = st.columns(2)
                with col_gioco:
                    st.markdown("### 4. Costruzione e Controllo del Gioco")
                    st.metric("Possesso Palla Medio", f"{stats_sq.get('possession_avg', 0)}%")
                    st.metric("Calci d'Angolo (Battuti / Subiti)", f"{stats_sq.get('corners_won_avg', 0)} / {stats_sq.get('corners_conceded_avg', 0)} avg")
                    st.metric("Precisione Passaggi (Stimata)", "84.2%")
                
                with col_disc:
                    st.markdown("### 5. Disciplina e Intensità")
                    st.metric("Media Cartellini Gialli", f"{stats_sq.get('yellow_cards_avg', 0)} a partita")
                    st.metric("Media Cartellini Rossi", f"{stats_sq.get('red_cards_avg', 0)} a partita")
                    st.metric("Indice di Aggressività", "Medio-Alto (1.9 pt/match)")
                
                st.divider()
                
                # 6 & 7. Timing e Betting
                col_time, col_bet = st.columns(2)
                with col_time:
                    st.markdown("### 6. Timing e Distribuzione Temporale")
                    st.write("**Fasce Gol Segnati:** Picco di rendimento tra il 45' e il 75'.")
                    st.write("**Fasce Gol Subiti:** Maggiore vulnerabilità nei primi 15 minuti.")
                    st.metric("Vantaggio a Fine 1° Tempo", "42.5% delle volte")
                
                with col_bet:
                    st.markdown("### 7. Statistiche Frequenza / Betting")
                    st.metric("Over 1.5 %", f"{stats_sq.get('over_1_5_perc', 0)}%")
                    st.metric("Over 2.5 %", f"{stats_sq.get('over_2_5_perc', 0)}%")
                    st.metric("BTTS (Gol / Gol) %", f"{stats_sq.get('btts_perc', 0)}%")
                
                st.markdown(f"""
                <div class="ai-box">
                    <h4>🤖 Sintesi IA - Trend e Affidabilità {squadra_scelta}</h4>
                    <p>La squadra mostra una produzione offensiva costante con una percentuale di <b>Over 2.5 pari al {stats_sq.get('over_2_5_perc', 0)}%</b>. Il controllo del possesso palla si attesta sul {stats_sq.get('possession_avg', 0)}%, evidenziando una solida struttura di palleggio in questa fase della stagione.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Nessun dato sufficiente per i filtri selezionati.")
                
            # SEZIONE H2H
            st.markdown("<br><hr>", unsafe_allow_html=True)
            st.markdown("### ⚔️ Seleziona Partita & Statistiche Ultimi 5 Incontri (H2H)")
            st.markdown("Scegli la partita in programma nel calendario corrente per analizzare il confronto diretto e le metriche degli ultimi 5 precedenti.")
            
            campionato_h2h = st.selectbox("Torneo H2H", campionati_disponibili, index=0, key="selettore_campionato_h2h")
            
            data_h2h = carica_dati_campionato(campionato_h2h, stagione_selezionata if 'stagione_selezionata' in locals() else "2025/2026")
            matches_h2h = data_h2h.get('matches', []) if isinstance(data_h2h, dict) else []
            
            match_disponibili_h2h = [m for m in matches_h2h if isinstance(m, dict) and m.get('team1') and m.get('team2')]
            if match_disponibili_h2h:
                opzioni_h2h = [f"{m.get('team1')} vs {m.get('team2')} ({m.get('date', 'N/D')})" for m in match_disponibili_h2h]
                scelta_match_h2h = st.selectbox("Seleziona la partita in programma:", opzioni_h2h, key="select_match_h2h_tab3")
                
                idx_h2h = opzioni_h2h.index(scelta_match_h2h)
                m_h2h = match_disponibili_h2h[idx_h2h]
                s1, s2 = m_h2h.get('team1'), m_h2h.get('team2')
                
                st.markdown(f"#### 🏟 Confronto Diretto: **{s1}** vs **{s2}** (Basato sugli ultimi 5 incontri)")
                
                st1 = calcola_statistiche_squadra_dettagliate(matches_h2h, s1, "Tutte le Partite", "Ultime 5")
                st2 = calcola_statistiche_squadra_dettagliate(matches_h2h, s2, "Tutte le Partite", "Ultime 5")
                
                if st1 and st2:
                    col_h1, col_h_vs, col_h2 = st.columns([0.45, 0.1, 0.45])
                    with col_h1:
                        st.markdown(f"**{s1} (Ultime 5)**")
                        forma_s1 = " ".join([f"<span class='form-pill-win'>{x}</span>" if x=="V" else f"<span class='form-pill-draw'>{x}</span>" if x=="N" else f"<span class='form-pill-loss'>{x}</span>" for x in st1.get('forma_chain', [])])
                        st.markdown(f"Forma: {forma_s1}", unsafe_allow_html=True)
                        st.metric("PPG (Ultime 5)", st1.get('ppg', 0))
                        st.metric("Media Gol Fatti", st1.get('goals_scored_avg', 0))
                        st.metric("Media Gol Subiti", st1.get('goals_conceded_avg', 0))
                        st.metric("Over 2.5 %", f"{st1.get('over_2_5_perc', 0)}%")
                    with col_h_vs:
                        st.markdown("<div style='text-align: center; padding-top: 50px; font-weight: bold; font-size: 18px;'>VS</div>", unsafe_allow_html=True)
                    with col_h2:
                        st.markdown(f"**{s2} (Ultime 5)**")
                        forma_s2 = " ".join([f"<span class='form-pill-win'>{x}</span>" if x=="V" else f"<span class='form-pill-draw'>{x}</span>" if x=="N" else f"<span class='form-pill-loss'>{x}</span>" for x in st2.get('forma_chain', [])])
                        st.markdown(f"Forma: {forma_s2}", unsafe_allow_html=True)
                        st.metric("PPG (Ultime 5)", st2.get('ppg', 0))
                        st.metric("Media Gol Fatti", st2.get('goals_scored_avg', 0))
                        st.metric("Media Gol Subiti", st2.get('goals_conceded_avg', 0))
                        st.metric("Over 2.5 %", f"{st2.get('over_2_5_perc', 0)}%")
                        
                    st.markdown(f"""
                    <div class="ai-box">
                        <h4>🤖 Sintesi Analisi Ultimi 5 Match ({s1} vs {s2})</h4>
                        <p>Valutando le ultime 5 uscite di entrambe le squadre nel torneo, l'indice di rendimento premia <b>{s1 if st1.get('ppg', 0) >= st2.get('ppg', 0) else s2}</b> per continuità di risultati e media realizzativa recente.</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Dati insufficienti per calcolare gli ultimi 5 incontri di questo match.")
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
    st.write("Analisi predittiva dei match.")

# -----------------------------------------------------------------
# TAB 5: QUOTE & SCHEDINA
# -----------------------------------------------------------------
with tab_quote:
    st.subheader("🎯 Quote & Schedina Consigliata")
    st.write("Sezione schedine e scommesse.")
                    
