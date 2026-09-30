    else:
      if prob_1 > 60:
        giocata_top = f"1 (Vittoria {t1})"
        motivazione_giocata = (
            f"Netta superiorità statistica e fattore campo a favore di {t1}."
        )
      elif prob_2 > 60:
        giocata_top = f"2 (Vittoria {t2})"
        motivazione_giocata = (
            f"Il rendimento esterno e i punti a partita (PPG) premiano {t2}."
        )
      else:
        giocata_top = "1X o Over 1.5 (Combo di Sicurezza)"
        motivazione_giocata = (
            "Partita estremamente equilibrata: prudente orientarsi su una"
            " doppia chance interna o su un Over 1.5 di base."
        )
          
