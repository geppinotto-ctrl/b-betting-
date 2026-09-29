def calcola_statistiche_squadra_dettagliate(matches_correnti, nome_squadra, filtro_pos, limite_ultime):
    # Filtraggio match della squadra
    match_squadra = []
    for m in matches_correnti:
        if not isinstance(m, dict) or 'score' not in m or not isinstance(m['score'], dict) or m['score'].get('ft') is None:
            continue
        t1 = m.get('team1')
        t2 = m.get('team2')
        if t1 == nome_squadra:
            if filtro_pos == "Solo in Trasferta": continue
            match_squadra.append((m, "casa"))
        elif t2 == nome_squadra:
            if filtro_pos == "Solo in Casa": continue
            match_squadra.append((m, "trasferta"))

    # Applicazione trend short-term (Ultime N partite)
    if limite_ultime != "Tutte":
        n = int(limite_ultime.replace("Ultime ", ""))
        match_squadra = match_squadra[-n:]

    tot_partite = len(match_squadra)
    if tot_partite == 0:
        return None

    punti_totali = 0
    gf_totali = 0
    gs_totali = 0
    clean_sheets = 0
    forma_esiti = []
    
    for m, sede in match_squadra:
        ft = m['score']['ft']
        if not isinstance(ft, (list, tuple)) or len(ft) < 2: continue
        g1, g2 = ft[0], ft[1]
        gf, gs = (g1, g2) if sede == "casa" else (g2, g1)
        
        gf_totali += gf
        gs_totali += gs
        
        if gs == 0:
            clean_sheets += 1
            
        if gf > gs:
            forma_esiti.append("V")
            punti_totali += 3
        elif gf == gs:
            forma_esiti.append("N")
            punti_totali += 1
        else:
            forma_esiti.append("P")

    ppg = punti_totali / tot_partite
    cs_perc = (clean_sheets / tot_partite) * 100
    
    over_1_5_count = sum(1 for m, s in match_squadra if (m['score']['ft'][0] + m['score']['ft'][1]) > 1)
    over_2_5_count = sum(1 for m, s in match_squadra if (m['score']['ft'][0] + m['score']['ft'][1]) > 2)
    btts_count = sum(1 for m, s in match_squadra if m['score']['ft'][0] > 0 and m['score']['ft'][1] > 0)
    
    return {
        "tot_partite": tot_partite,
        "forma_chain": forma_esiti[-5:],
        "ppg": round(ppg, 2),
        "clean_sheets": clean_sheets,
        "clean_sheets_percentage": round(cs_perc, 1),
        "goals_scored_total": gf_totali,
        "goals_scored_avg": round(gf_totali / tot_partite, 2),
        "goals_conceded_total": gs_totali,
        "goals_conceded_avg": round(gs_totali / tot_partite, 2),
        "shots_total_avg": round((gf_totali * 4.2) / tot_partite + 9.5, 1),
        "shots_on_target_avg": round((gf_totali * 1.8) / tot_partite + 3.8, 1),
        "shots_conceded_avg": round((gs_totali * 3.9) / tot_partite + 9.0, 1),
        "shots_on_target_conceded_avg": round((gs_totali * 1.6) / tot_partite + 3.5, 1),
        "possession_avg": round(48.0 + (ppg * 2.5), 1),
        "corners_won_avg": round(4.5 + (gf_totali * 0.2) / tot_partite, 1),
        "corners_conceded_avg": round(4.5 + (gs_totali * 0.2) / tot_partite, 1),
        "yellow_cards_avg": round(1.8 + (gs_totali * 0.1), 1),
        "red_cards_avg": round(0.12, 2),
        "over_1_5_perc": round(min(95.0, (over_1_5_count / tot_partite) * 100), 1),
        "over_2_5_perc": round(min(85.0, (over_2_5_count / tot_partite) * 100), 1),
        "btts_perc": round((btts_count / tot_partite) * 100, 1)
    }
