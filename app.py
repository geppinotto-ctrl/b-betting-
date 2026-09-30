# Filtriamo solo le partite che non hanno ancora un risultato (quindi future / da giocare)
    # oppure con data maggiore o uguale a oggi, escludendo quelle già scadute.
    oggi_str = now.strftime('%Y-%m-%d')
    
    match_prossima_giornata = []
    for m in matches:
      if isinstance(m, dict) and m.get("team1") and m.get("team2"):
        # Controlliamo che non ci sia già un risultato finale registrato (ft)
        # e che la data sia odierna o futura (se la data è presente)
        data_match = m.get("date", "")
        ha_risultato = "score" in m and isinstance(m["score"], dict) and m["score"].get("ft") is not None
        
        # Se la partita non ha ancora un risultato, è un evento futuro/da disputare
        if not ha_risultato:
          # Opzionale: se vuoi filtrare rigorosamente per data >= oggi (formato stringa YYYY-MM-DD funziona benissimo)
          if not data_match or data_match >= oggi_str:
            match_prossima_giornata.append(m)

    # Se per caso il campionato è finito o non ci sono match futuri, diamo comunque la possibilità di vedere qualcosa per non bloccare l'app
    if not match_prossima_giornata:
      match_prossima_giornata = [m for m in matches if isinstance(m, dict) and m.get("team1") and m.get("team2")]

    if match_prossima_giornata:
      match_options = []
      match_dict = {}
      for m in match_prossima_giornata:
        t1 = m.get("team1")
        t2 = m.get("team2")
        # Mostriamo solo le squadre senza la data davanti nel menu a tendina
        label = f"{t1} vs {t2}"
        match_options.append(label)
        match_dict[label] = m

      st.markdown("🎯 *Seleziona una partita per il Confronto Diretto e Pronostico IA:*")

      partita_scelta_label = st.selectbox(
          "Seleziona la Partita della Giornata",
          match_options,
          key="match_scelto_stat",
      )
      m_sel = match_dict[partita_scelta_label]
      t1 = m_sel.get("team1")
      t2 = m_sel.get("team2")

      stats_t1 = calcola_statistiche_squadra(matches, t1)
      stats_t2 = calcola_statistiche_squadra(matches, t2)
      prob_1, prob_x, prob_2 = calcola_pronostico_ia(stats_t1, stats_t2)

      st.markdown("---")
      st.markdown(f"### ⚔️ Confronto Diretto: {t1} vs {t2}")

      col_s1, col_s2 = st.columns(2)

      with col_s1:
        st.markdown(f"#### 🏠 {t1}")
        if stats_t1:
          st.metric("Punti a Partita (PPG)", stats_t1["ppg"])
          st.metric("Media Gol Fatti", stats_t1["gf_avg"])
          st.metric("Media Gol Subiti", stats_t1["gs_avg"])
          st.metric("Over 2.5 %", f"{stats_t1['over_2_5_pct']}%")
          st.metric("Clean Sheet %", f"{stats_t1['clean_sheets_pct']}%")
          st.metric("Gol a Partita (BTTS %)", f"{stats_t1['btts_pct']}%")

          st.markdown("**Stato di Forma (Ultime 5):**")
          forma_html_1 = ""
          for ris in stats_t1["forma"][-5:]:
            if ris == "V":
              forma_html_1 += "<span class='badge-v'>V</span>"
            elif ris == "N":
              forma_html_1 += "<span class='badge-n'>N</span>"
            else:
              forma_html_1 += "<span class='badge-p'>P</span>"
          st.markdown(
              forma_html_1 if forma_html_1 else "N.D.", unsafe_allow_html=True
          )

          st.markdown(
              "<br>**Barra Statistiche Squadra:**", unsafe_allow_html=True
          )
          st.progress(
              min(max(int(stats_t1["ppg"] / 3.0 * 100), 0), 100),
              text=f"Indice Rendimento: {stats_t1['ppg']} PPG",
          )
        else:
          st.info("Dati insufficienti per questa squadra.")

      with col_s2:
        st.markdown(f"#### ✈️ {t2}")
        if stats_t2:
          st.metric("Punti a Partita (PPG)", stats_t2["ppg"])
          st.metric("Media Gol Fatti", stats_t2["gf_avg"])
          st.metric("Media Gol Subiti", stats_t2["gs_avg"])
          st.metric("Over 2.5 %", f"{stats_t2['over_2_5_pct']}%")
          st.metric("Clean Sheet %", f"{stats_t2['clean_sheets_pct']}%")
          st.metric("Gol a Partita (BTTS %)", f"{stats_t2['btts_pct']}%")

          st.markdown("**Stato di Forma (Ultime 5):**")
          forma_html_2 = ""
          for ris in stats_t2["forma"][-5:]:
            if ris == "V":
              forma_html_2 += "<span class='badge-v'>V</span>"
            elif ris == "N":
              forma_html_2 += "<span class='badge-n'>N</span>"
            else:
              forma_html_2 += "<span class='badge-p'>P</span>"
          st.markdown(
              forma_html_2 if forma_html_2 else "N.D.", unsafe_allow_html=True
          )

          st.markdown(
              "<br>**Barra Statistiche Squadra:**", unsafe_allow_html=True
          )
          st.progress(
              min(max(int(stats_t2["ppg"] / 3.0 * 100), 0), 100),
              text=f"Indice Rendimento: {stats_t2['ppg']} PPG",
          )
        else:
          st.info("Dati insufficienti per questa squadra.")

      st.markdown("---")
      try:
        if 't1' in locals() and 't2' in locals() and 'prob_1' in locals():
          analisi_testo = genera_analisi_ia_match(
              t1, t2, stats_t1, stats_t2, prob_1, prob_x, prob_2
          )
          html_output = f"<div class='ai-box'>{analisi_testo}<br><b>Previsioni Esito 1X2:</b><br>• {t1} (1): <b>{prob_1}%</b><br>• Pareggio (X): <b>{prob_x}%</b><br>• {t2} (2): <b>{prob_2}%</b></div>"
          st.markdown(html_output, unsafe_allow_html=True)
        else:
          st.info("Seleziona una partita dal menu per sbloccare l'analisi IA.")
      except Exception as e:
        st.info("Modulo di analisi pronto all'uso.")
