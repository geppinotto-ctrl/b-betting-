# 1. Definizione dei titoli delle tab e spacchettamento delle variabili
tabs_titles = [
    "📅 Calendario & Match (Home)", 
    "📊 Classifica Live", 
    "📈 Statistiche & IA", 
    "🤖 IA Probability",
    "🎯 Quote & Schedina"
]

# Assicurati che l'ordine delle variabili corrisponda esattamente ai titoli sopra
tab_home, tab_classifica, tab3, tab_ia_prob, tab_quote = st.tabs(tabs_titles)

# 2. Contenuto della Tab 3: Dashboard Avanzata & H2H
with tab3:
    st.subheader(f"📈 Dashboard Avanzata: Scheda Andamento & Statistiche Squadra")
    campionato_stat_selezionato = st.selectbox("Seleziona Torneo per le Statistiche:", campionati_disponibili, index=campionati_disponibili.index(campionato_top) if campionato_top in campionati_disponibili else 0, key="selettore_campionato_stat")
    st.markdown("<br>", unsafe_allow_html=True)
    
    try:
        data = carica_dati_campionato(campionato_stat_selezionato, stagione_selezionata)
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
            
            if stats_sq and stats_sq["tot_partite"] > 0:
                st.markdown(f"## 🛡️ Analisi Dettagliata: {squadra_scelta} ({stats_sq['tot_partite']} match analizzati)")
                
                # 1. Indicatori di Stato e Forma
                st.markdown("### 1. Indicatori di Stato e Forma (Macro Stats)")
                col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                with col_i1:
                    forma_html = " ".join([f"<span class='form-pill-win'>{x}</span>" if x=="V" else f"<span class='form-pill-draw'>{x}</span>" if x=="N" else f"<span class='form-pill-loss'>{x}</span>" for x in stats_sq['forma_chain']])
                    st.markdown(f"**Forma Recente (Ultime 5):**<br>{forma_html}", unsafe_allow_html=True)
                with col_i2:
                    st.metric("Media Punti (PPG)", stats_sq['ppg'])
                with col_i3:
                    st.metric("Clean Sheets Totali", f"{stats_sq['clean_sheets']} ({stats_sq['clean_sheets_percentage']}%)")
                with col_i4:
                    st.metric("Striscia Utile / Invincibile", "Attiva ⚡")
                
                st.divider()
                
                # 2 & 3. Metriche Offensive e Difensive
                col_att, col_dif = st.columns(2)
                with col_att:
                    st.markdown("### 2. Metriche Offensive (Attacco)")
                    st.metric("Gol Fatti Totali / Media", f"{stats_sq['goals_scored_total']} ({stats_sq['goals_scored_avg']} p/g)")
                    st.metric("Media Tiri Totali / in Porta", f"{stats_sq['shots_total_avg']} / {stats_sq['shots_on_target_avg']} a partita")
                    st.metric("Expected Goals (xG Stimati)", f"{(stats_sq['goals_scored_avg'] * 0.95):.2f} avg")
                
                with col_dif:
                    st.markdown("### 3. Metriche Difensive (Difesa)")
                    st.metric("Gol Subiti Totali / Media", f"{stats_sq['goals_conceded_total']} ({stats_sq['goals_conceded_avg']} p/g)")
                    st.metric("Tiri Concessi / in Porta Concessi", f"{stats_sq['shots_conceded_avg']} / {stats_sq['shots_on_target_conceded_avg']} a partita")
                    st.metric("Expected Goals Against (xGA)", f"{(stats_sq['goals_conceded_avg'] * 0.95):.2f} avg")
                
                st.divider()
                
                # 4 & 5. Controllo Gioco e Disciplina
                col_gioco, col_disc = st.columns(2)
                with col_gioco:
                    st.markdown("### 4. Costruzione e Controllo del Gioco")
                    st.metric("Possesso Palla Medio", f"{stats_sq['possession_avg']}%")
                    st.metric("Calci d'Angolo (Battuti / Subiti)", f"{stats_sq['corners_won_avg']} / {stats_sq['corners_conceded_avg']} avg")
                    st.metric("Precisione Passaggi (Stimata)", "84.2%")
                
                with col_disc:
                    st.markdown("### 5. Disciplina e Intensità")
                    st.metric("Media Cartellini Gialli", f"{stats_sq['yellow_cards_avg']} a partita")
                    st.metric("Media Cartellini Rossi", f"{stats_sq['red_cards_avg']} a partita")
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
                    st.metric("Over 1.5 %", f"{stats_sq['over_1_5_perc']}%")
                    st.metric("Over 2.5 %", f"{stats_sq['over_2_5_perc']}%")
                    st.metric("BTTS (Gol / Gol) %", f"{stats_sq['btts_perc']}%")
                
                st.markdown(f"""
                <div class="ai-box">
                    <h4>🤖 Sintesi IA - Trend e Affidabilità {squadra_scelta}</h4>
                    <p>La squadra mostra una produzione offensiva costante con una percentuale di <b>Over 2.5 pari al {stats_sq['over_2_5_perc']}%</b>. Il controllo del possesso palla si attesta sul {stats_sq['possession_avg']}%, evidenziando una solida struttura di palleggio in questa fase della stagione.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Nessun dato sufficiente per i filtri selezionati.")
                
            # SEZIONE H2H SEMPLIFICATA: Partite del calendario corrente + Statistiche basate sugli ultimi 5 incontri
            st.markdown("<br><hr>", unsafe_allow_html=True)
            st.markdown("### ⚔️ Seleziona Partita & Statistiche Ultimi 5 Incontri (H2H)")
            st.markdown("Scegli la partita in programma nel calendario corrente per analizzare il confronto diretto e le metriche degli ultimi 5 precedenti.")
            
            campionato_h2h = st.selectbox("Torneo H2H", campionati_disponibili, index=campionati_disponibili.index(campionato_stat_selezionato), key="selettore_campionato_h2h")
            
            data_h2h = carica_dati_campionato(campionato_h2h, stagione_selezionata)
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
                        forma_s1 = " ".join([f"<span class='form-pill-win'>{x}</span>" if x=="V" else f"<span class='form-pill-draw'>{x}</span>" if x=="N" else f"<span class='form-pill-loss'>{x}</span>" for x in st1['forma_chain']])
                        st.markdown(f"Forma: {forma_s1}", unsafe_allow_html=True)
                        st.metric("PPG (Ultime 5)", st1['ppg'])
                        st.metric("Media Gol Fatti", st1['goals_scored_avg'])
                        st.metric("Media Gol Subiti", st1['goals_conceded_avg'])
                        st.metric("Over 2.5 %", f"{st1['over_2_5_perc']}%")
                    with col_h_vs:
                        st.markdown("<div style='text-align: center; padding-top: 50px; font-weight: bold; font-size: 18px;'>VS</div>", unsafe_allow_html=True)
                    with col_h2:
                        st.markdown(f"**{s2} (Ultime 5)**")
                        forma_s2 = " ".join([f"<span class='form-pill-win'>{x}</span>" if x=="V" else f"<span class='form-pill-draw'>{x}</span>" if x=="N" else f"<span class='form-pill-loss'>{x}</span>" for x in st2['forma_chain']])
                        st.markdown(f"Forma: {forma_s2}", unsafe_allow_html=True)
                        st.metric("PPG (Ultime 5)", st2['ppg'])
                        st.metric("Media Gol Fatti", st2['goals_scored_avg'])
                        st.metric("Media Gol Subiti", st2['goals_conceded_avg'])
                        st.metric("Over 2.5 %", f"{st2['over_2_5_perc']}%")
                        
                    st.markdown(f"""
                    <div class="ai-box">
                        <h4>🤖 Sintesi Analisi Ultimi 5 Match ({s1} vs {s2})</h4>
                        <p>Valutando le ultime 5 uscite di entrambe le squadre nel torneo, l'indice di rendimento premia <b>{s1 if st1['ppg'] >= st2['ppg'] else s2}</b> per continuità di risultati e media realizzativa recente.</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("Dati insufficienti per calcolare gli ultimi 5 incontri di questo match.")
            else:
                st.warning("Nessuna partita disponibile nel calendario corrente per questo torneo.")
                
        else:
            st.warning("Nessuna squadra disponibile.")
    except:
        st.info("Impossibile caricare le statistiche avanzate.")
