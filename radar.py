from collections import Counter
from datetime import timedelta

import pandas as pd
import streamlit as st

from config import ODDS_API_KEY, adesso, stagione_corrente, torneo_corrente
from dati import carica_stats_extra, trova_nome_fd
from grafici import CSS_GRAFICI, radar_card_html
from modello import calcola_forze, esiti_poisson, forze_tiri, gol_attesi
from quote import (
    carica_quote_api,
    catalogo_da_evento,
    evento_da_indice,
    indice_eventi_quote,
    prob_mercato,
)

PESO_MERCATO = 0.5  # nella stima "prudente" il mercato pesa quanto il modello


def calcola_radar(matches, giorni, solo_italia, peso_mercato=PESO_MERCATO):
    """Ritorna (righe, messaggio, partite_analizzate).

    Ogni riga è un esito (1, X o 2) di una partita con quote:
    EV = probabilità x quota - 1. L'EV 'prudente' usa una probabilità mista
    (modello e mercato), perché il modello da solo tende a sbagliare proprio
    dove sembra più sicuro.
    """
    modello = calcola_forze(matches)
    if not modello:
        return [], "Servono più partite giocate per stimare il modello.", 0
    if not ODDS_API_KEY:
        return [], "Chiave ODDS_API_KEY non trovata nei Secrets.", 0
    res = carica_quote_api(ODDS_API_KEY)
    if not res["ok"]:
        return [], f"Quote non disponibili: {res['errore']}", 0
    indice = indice_eventi_quote(res["odds"])

    df = carica_stats_extra(torneo_corrente(), stagione_corrente())
    tiri = forze_tiri(df)
    nomi = set()
    if tiri is not None and df is not None:
        nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
    cache_nomi = {}

    def nome_fd(t):
        if t not in cache_nomi:
            cache_nomi[t] = trova_nome_fd(t, nomi) if nomi else None
        return cache_nomi[t]

    giocate = Counter()
    for m in matches:
        sc = m.get("score") if isinstance(m, dict) else None
        if isinstance(sc, dict) and sc.get("ft"):
            giocate[m.get("team1")] += 1
            giocate[m.get("team2")] += 1

    ora = adesso()
    oggi = ora.strftime("%Y-%m-%d")
    limite = (ora + timedelta(days=giorni)).strftime("%Y-%m-%d")
    righe, analizzate = [], 0
    for m in matches:
        if not isinstance(m, dict) or not m.get("team1") or not m.get("team2"):
            continue
        sc = m.get("score")
        if isinstance(sc, dict) and sc.get("ft"):
            continue
        data = str(m.get("date") or "")[:10]
        if data < oggi or data > limite:
            continue
        t1, t2 = m["team1"], m["team2"]
        if t1 not in modello["forze"] or t2 not in modello["forze"]:
            continue
        ev = evento_da_indice(indice, t1, t2)
        if ev is None:
            continue
        cat = catalogo_da_evento(ev, solo_italia)
        pm = prob_mercato(cat, "Esito finale 1X2", ["1", "X", "2"])
        if not pm:
            continue
        analizzate += 1
        l1, l2, _ = gol_attesi(modello, t1, t2, tiri, nome_fd(t1), nome_fd(t2), usa_assenze=True)
        e = esiti_poisson(l1, l2)
        campione = min(giocate[t1], giocate[t2])
        for g in ("1", "X", "2"):
            p_mod, p_mkt = e[g], pm[0][g]
            book, q = max(cat["Esito finale 1X2"][g].items(), key=lambda x: x[1])
            p_pru = (1 - peso_mercato) * p_mod + peso_mercato * p_mkt
            righe.append({
                "Data": data,
                "Partita": f"{t1} - {t2}",
                "Esito": g,
                "Quota": round(q, 2),
                "Bookmaker": book,
                "Modello %": round(p_mod, 1),
                "Mercato %": round(p_mkt, 1),
                "Scarto": round(p_mod - p_mkt, 1),
                "EV modello %": round((p_mod / 100 * q - 1) * 100, 1),
                "EV prudente %": round((p_pru / 100 * q - 1) * 100, 1),
                "Campione": campione,
                "_t1": t1,
                "_t2": t2,
            })
    return righe, "", analizzate


def mostra_radar_valore(matches, tab):
    with tab:
        st.subheader("📡 Radar valore")
        st.caption(
            "Esiti in cui il modello stima una probabilità più alta del mercato e la "
            "quota paga più del 'giusto'. È un elenco di partite da approfondire, non "
            "una previsione: il modello non conosce formazioni e infortuni. Nella tab "
            "Backtest, sezione «Modello contro mercato», vedi come sarebbero andate "
            "queste regole sulle partite passate."
        )
        if not matches:
            st.info("Nessuna partita disponibile.")
            return

        chiave = f"{torneo_corrente()}_{stagione_corrente()}"
        c1, c2 = st.columns(2)
        with c1:
            finestra = st.selectbox(
                "Partite in arrivo",
                ["Prossimi 7 giorni", "Prossimi 14 giorni", "Prossimi 30 giorni"],
                key=f"radar_finestra_{chiave}",
            )
        with c2:
            min_camp = st.selectbox(
                "Partite giocate minime",
                [3, 5, 8],
                index=1,
                key=f"radar_campione_{chiave}",
            )
        c3, c4 = st.columns(2)
        with c3:
            prob_min = st.selectbox(
                "Probabilità minima modello %",
                [15, 20, 25, 30],
                index=1,
                key=f"radar_probmin_{chiave}",
            )
        with c4:
            solo_it = st.checkbox(
                "Solo bookmaker italiani (ADM)", value=True, key=f"radar_it_{chiave}"
            )
        solo_pos = st.checkbox(
            "Solo segnali con EV prudente positivo", value=True, key=f"radar_pos_{chiave}"
        )

        giorni = int(finestra.split()[1])
        righe, messaggio, analizzate = calcola_radar(matches, giorni, solo_it)
        if messaggio:
            st.info(messaggio)
            return
        if not righe:
            st.info(
                "Nessuna partita con quote nel periodo scelto: le quote di solito "
                "sono disponibili solo per le gare dei prossimi giorni."
            )
            return

        con_campione = [r for r in righe if r["Campione"] >= min_camp]
        scartate = len({(r["Data"], r["Partita"]) for r in righe}) - len(
            {(r["Data"], r["Partita"]) for r in con_campione}
        )
        filtrate = [r for r in con_campione if r["Modello %"] >= prob_min and r["Scarto"] > 0]
        if solo_pos:
            filtrate = [r for r in filtrate if r["EV prudente %"] > 0]
        filtrate.sort(key=lambda r: r["EV prudente %"], reverse=True)

        st.caption(
            f"Partite con quote analizzate: {analizzate}"
            + (f" · escluse per poche partite giocate: {scartate}" if scartate else "")
            + f" · segnali: {len(filtrate)}"
        )
        if not filtrate:
            st.info(
                "Nessun segnale con questi filtri. Succede spesso, ed è un buon "
                "segno di prudenza: se vuoi vedere di più allarga la finestra o "
                "togli il filtro sull'EV prudente."
            )
            return

        st.markdown(
            CSS_GRAFICI + "".join(radar_card_html(r) for r in filtrate[:8]),
            unsafe_allow_html=True,
        )
        with st.expander(f"Tutti i segnali ({len(filtrate)})"):
            st.dataframe(
                pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in filtrate]),
                use_container_width=True,
                hide_index=True,
            )
        st.caption(
            "EV = probabilità x quota - 1. EV modello usa la sola stima del modello; "
            "EV prudente la mescola al 50% con il mercato, perché gli scarti più "
            "grandi sono spesso errori del modello. Scarto = modello meno mercato, in "
            "punti. Nessun segnale è una garanzia. Solo maggiorenni: gioca "
            "responsabilmente e solo somme che puoi permetterti di perdere."
        )
