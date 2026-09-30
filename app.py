    if btts_consigliato:
      giocata_top = "GOAL (Entrambe le squadre a segno)"
      motivazione_giocata = (
          f"Le medie realizzative di {t1} e {t2} unite alle percentuali di BTTS"
          " elevate (>55%) rendono altamente probabile reti da ambo i lati."
      )
    elif over_consigliato:
      giocata_top = "OVER 2.5"
      motivazione_giocata = (
          f"Il volume offensivo complessivo ({round(media_gol_totale, 2)} gol"
          " attesi combinati) suggerisce un match aperto e ricco di marcature."
      )
    else:
      if prob_1 > 60:
        giocata_top = "1 (Vittoria Casa)"
        motivazione_giocata = (
            f"Netta superiorità statistica e fattore campo per {t1}."
        )
      elif prob_2 > 60:
        giocata_top = "2 (Vittoria Ospite)"
        motivazione_giocata = (
            f"Fattore esterno favorevole e momento positivo per {t2}."
        )
      else:
        giocata_top = "1X / Double Chance"
        motivazione_giocata = (
            "Partita equilibrata: la doppia chance interna offre buon"
            " valore di copertura."
        )

    st.markdown(
        f"""
        <div class='smart-tip-box'>
            <h4 style='color: #58a6ff; margin-top: 0;'>💡 Smart Tip IA Consigliata</h4>
            <p style='font-size: 16px; margin-bottom: 8px;'>Esito Consigliato: <b>{giocata_top}</b></p>
            <p style='color: #8b949e; font-size: 14px; margin-bottom: 0;'>{motivazione_giocata}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
