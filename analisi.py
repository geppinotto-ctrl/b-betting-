from datetime import timedelta
import assenze
import pandas as pd
import streamlit as st
import persistenza
import valore
from registro import bottone_registra, da_consigli
from config import ODDS_API_KEY, adesso, stagione_corrente, torneo_corrente
from dati import calcola_stats_extra, carica_dati_campionato, carica_stats_extra, trova_nome_fd
from confronto_mercato import mostra_backtest_mercato
from grafici import mostra_grafici_partita, schede_riepilogo
from modello import _giocate_ordinate, calcola_forze, calcola_statistiche_squadra, calcola_stats_tempi, esegui_backtest, esiti_poisson, firma_dati, forze_tiri, genera_analisi_v2, gol_attesi, probabilita_v2, raccogli_consigli, riassumi_backtest, sintesi_dna_pronostico, stelle_difficolta, stelle_multipla, trova_scontri_diretti
from radar import mostra_radar_valore
from quote import carica_quote_api, catalogo_da_evento, evento_da_indice, indice_eventi_quote, mostra_quote_confronto, mostra_quote_prepartita, prob_mercato
from schedina import mostra_schedina
from resilienza import (
    ERRORE, OBSOLETO, abbastanza_partite, mostra_stato_dati, sezione_sicura,
)
from stile import badge_squadra


def mostra_metriche_squadra(titolo, stats):
    st.markdown(titolo, unsafe_allow_html=True)
    if stats:
        st.metric("Punti a Partita (PPG)", stats["ppg"])
        st.metric("Media Gol Fatti", stats["gf_avg"])
        st.metric("Media Gol Subiti", stats["gs_avg"])
        st.metric("Over 2.5 %", f"{stats['over_2_5_pct']}%")
        st.metric("Clean Sheet %", f"{stats['clean_sheets_pct']}%")
        st.metric("BTTS %", f"{stats['btts_pct']}%")
    else:
        st.info("Dati insufficienti per questa squadra.")


def mostra_scontri_diretti(campionato, t1, t2):
    st.markdown("#### 🤝 Ultimi scontri diretti")
    scontri = trova_scontri_diretti(campionato, t1, t2)
    if not scontri:
        st.info("Nessuno scontro diretto trovato nelle ultime stagioni.")
        return

    v1, v2, pa = 0, 0, 0
    righe = []
    for data, casa, osp, g1, g2 in scontri:
        if g1 == g2:
            pa += 1
        elif (g1 > g2 and casa == t1) or (g2 > g1 and osp == t1):
            v1 += 1
        else:
            v2 += 1
        righe.append({"Data": data, "Partita": f"{casa} {g1}-{g2} {osp}"})

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Vittorie {t1}", v1)
    c2.metric("Pareggi", pa)
    c3.metric(f"Vittorie {t2}", v2)
    st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)


def mostra_grafico_forma(dati, n=10):
    st.markdown(f"#### 📈 Andamento punti (ultime {n} partite)")
    valori = {"V": 3, "N": 1, "P": 0}
    serie = {}
    for nome, stats in dati.items():
        if stats and stats["forma"]:
            totale = 0
            cumulati = []
            for r in stats["forma"][-n:]:
                totale += valori[r]
                cumulati.append(totale)
            serie[nome] = cumulati

    if not serie:
        st.info("Dati insufficienti per il grafico.")
        return

    df = pd.DataFrame({k: pd.Series(v) for k, v in serie.items()})
    df.index = range(1, len(df) + 1)
    df.index.name = "Partita"
    st.line_chart(df)


def mostra_stats_tempi(titolo, stats):
    st.markdown(titolo)
    if not stats:
        st.info("Dati del primo tempo non disponibili.")
        return
    df = pd.DataFrame(
        {
            "Tempo": ["1° tempo", "2° tempo"],
            "Fatti (media)": [stats["gf1"], stats["gf2"]],
            "Subiti (media)": [stats["gs1"], stats["gs2"]],
        }
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.metric("Segna nel 1° tempo", f"{stats['segna_1t_pct']}%")
    st.caption(f"Calcolato su {stats['tot']} partite con dato del primo tempo.")


def mostra_stats_extra(titolo, nome):
    st.markdown(titolo)
    df = carica_stats_extra(torneo_corrente(), stagione_corrente())
    if df is None:
        st.info(
            "Statistiche aggiuntive disponibili solo per la Serie A "
            "e se la stagione ha i dati."
        )
        return
    stats = calcola_stats_extra(df, nome)
    if not stats:
        st.warning(f"Squadra '{nome}' non riconosciuta nei dati aggiuntivi.")
        return

    def v(x):
        return "-" if x is None else str(x)

    tabella = pd.DataFrame(
        [
            {"Statistica": "Calci d'angolo", "Fatti": v(stats["angoli_f"]), "Subiti": v(stats["angoli_s"])},
            {"Statistica": "Tiri", "Fatti": v(stats["tiri_f"]), "Subiti": v(stats["tiri_s"])},
            {"Statistica": "Tiri in porta", "Fatti": v(stats["porta_f"]), "Subiti": v(stats["porta_s"])},
            {"Statistica": "Falli commessi", "Fatti": v(stats["falli"]), "Subiti": "-"},
            {"Statistica": "Cartellini gialli", "Fatti": v(stats["gialli"]), "Subiti": "-"},
            {"Statistica": "Cartellini rossi", "Fatti": v(stats["rossi"]), "Subiti": "-"},
        ]
    )
    st.dataframe(tabella, use_container_width=True, hide_index=True)
    st.caption(
        f"Media su {stats['tot']} partite. Fonte: football-data.co.uk "
        f"(nome nei dati: {stats['nome_fd']})."
        )


def mostra_dna_pronostico(t1, t2, dettagli):
    if not dettagli:
        st.info("🧬 DNA del pronostico non disponibile.")
        return

    l1 = dettagli.get("l1")
    l2 = dettagli.get("l2")
    e = dettagli.get("e", {})
    usato_tiri = dettagli.get("tiri", False)

    mc = dettagli.get("mc")
    mf = dettagli.get("mf")
    att1 = dettagli.get("att1")
    dif1 = dettagli.get("dif1")
    att2 = dettagli.get("att2")
    dif2 = dettagli.get("dif2")

    def lettura_attacco(v):
        if v is None:
            return ""
        if v > 1:
            return "sopra il riferimento"
        if v < 1:
            return "sotto il riferimento"
        return "in linea con il riferimento"

    def lettura_gol_concessi(v):
        if v is None:
            return ""
        if v > 1:
            return "concede più gol del riferimento"
        if v < 1:
            return "concede meno gol del riferimento"
        return "in linea con il riferimento"

    st.markdown("### 🧬 DNA DEL PRONOSTICO")

    st.markdown("#### ⚽ Gol attesi")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(t1, f"{l1:.2f}")

    with col2:
        st.metric(t2, f"{l2:.2f}")

    st.markdown("#### 🧬 Forze del modello")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{t1}**")
        st.write(f"⚔️ Attacco: **{att1:.3f}×**")
        st.caption(f"↳ {lettura_attacco(att1)}")

        st.write(f"🛡️ Gol concessi: **{dif1:.3f}×**")
        st.caption(f"↳ {lettura_gol_concessi(dif1)}")

    with col2:
        st.markdown(f"**{t2}**")
        st.write(f"⚔️ Attacco: **{att2:.3f}×**")
        st.caption(f"↳ {lettura_attacco(att2)}")

        st.write(f"🛡️ Gol concessi: **{dif2:.3f}×**")
        st.caption(f"↳ {lettura_gol_concessi(dif2)}")

    st.markdown("#### 🏟️ Media gol del campionato")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Casa", f"{mc:.2f}")

    with col2:
        st.metric("Trasferta", f"{mf:.2f}")

    st.markdown("#### 📊 Esiti elaborati")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("1 — Casa", f"{e.get('1', 0):.1f}%")

    with col2:
        st.metric("X — Pareggio", f"{e.get('X', 0):.1f}%")

    with col3:
        st.metric("2 — Trasferta", f"{e.get('2', 0):.1f}%")

    if usato_tiri:
        st.success("🎯 Modulo tiri integrato — peso 30%")
    else:
        st.info("🎯 Modulo tiri non disponibile — modello basato sui gol")

    st.markdown("#### 🧠 Lettura del modello")

    st.markdown(
        f"""
        <div style="
            padding: 14px 18px;
            border-left: 3px solid rgba(255,255,255,0.35);
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            margin-top: 8px;
            margin-bottom: 12px;
        ">
            {sintesi_dna_pronostico(t1, t2, dettagli)}
        </div>
        """,
        unsafe_allow_html=True
    )

    top = e.get("top", [])

    if top:
        st.markdown("#### 🎯 Risultati esatti più probabili")

        dati_top = []

        for risultato, probabilita in top:
            dati_top.append({
                "Risultato": risultato,
                "Probabilità": f"{probabilita * 100:.2f}%"
            })

        st.dataframe(
            pd.DataFrame(dati_top),
            hide_index=True,
            use_container_width=True
                                     )


def mostra_pronostico_v2(matches, t1, t2):
    st.markdown("### 🧠 Pronostico v2 (modello di Poisson)")
    modello = calcola_forze(matches)
    if not modello or t1 not in modello["forze"] or t2 not in modello["forze"]:
        st.info("Servono più partite giocate per stimare il modello.")
        return

    df = carica_stats_extra(torneo_corrente(), stagione_corrente())
    tiri = forze_tiri(df)
    nome1 = nome2 = None
    if tiri is not None and df is not None:
        nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
        nome1 = trova_nome_fd(t1, nomi)
        nome2 = trova_nome_fd(t2, nomi)

    l1, l2, usato_tiri = gol_attesi(modello, t1, t2, tiri, nome1, nome2, usa_assenze=True)
    e = esiti_poisson(l1, l2)

    def riga(nome, p):
        quota = f"{100 / p:.2f}" if p > 0.1 else "-"
        return {"Mercato": nome, "Probabilità": f"{p:.1f}%", "Quota equa": quota}

    tabella = pd.DataFrame(
        [
            riga(f"1 - {t1}", e["1"]),
            riga("X - Pareggio", e["X"]),
            riga(f"2 - {t2}", e["2"]),
            riga("Over 2.5", e["over25"]),
            riga("Under 2.5", e["under25"]),
            riga("Goal (segnano entrambe)", e["goal"]),
            riga("NoGoal", e["nogoal"]),
        ]
    )
    st.dataframe(tabella, use_container_width=True, hide_index=True)

    st.markdown("**Risultati esatti più probabili**")
    top = pd.DataFrame(
        [{"Risultato": r, "Probabilità": f"{p * 100:.1f}%"} for r, p in e["top"]]
    )
    st.dataframe(top, use_container_width=True, hide_index=True)

    base = "con tiri in porta (peso 30%)" if usato_tiri else "solo sui gol"
    st.caption(
        f"Gol attesi: {t1} {l1:.2f} - {t2} {l2:.2f}. Calcolo {base}, "
        "con più peso alle partite recenti. La quota equa è 100 diviso la "
        "probabilità, cioè senza il margine del bookmaker. È una stima, "
        "non una garanzia."
    )
    nota_assenze = assenze.descrivi(t1, t2, assenze.assenze_attive())
    if nota_assenze:
        st.caption("🩹 " + nota_assenze)


def mostra_riepilogo(matches, tab):
    with tab:
        st.subheader("🎯 Riepilogo Pronostici")
        modello = calcola_forze(matches)
        if not modello:
            st.info("Servono più partite giocate per stimare il modello.")
            return

        oggi = adesso().strftime("%Y-%m-%d")
        c1, c2 = st.columns(2)
        with c1:
            giorni = st.selectbox(
                "Partite in arrivo",
                ["Prossimi 7 giorni", "Prossimi 14 giorni", "Prossimi 30 giorni", "Tutte"],
                index=1,
                key=f"riep_giorni_{torneo_corrente()}_{stagione_corrente()}",
            )
        with c2:
            ordine = st.selectbox(
                "Ordina per",
                ["Probabilità più alta", "Scarto dal mercato", "Data", "Over 2.5", "Goal"],
                key=f"riep_ordine_{torneo_corrente()}_{stagione_corrente()}",
            )

        limite = None
        if giorni != "Tutte":
            n = int(giorni.split()[1])
            limite = (adesso() + timedelta(days=n)).strftime("%Y-%m-%d")

        prossime = [
            m
            for m in matches
            if isinstance(m, dict)
            and m.get("team1")
            and m.get("team2")
            and not (isinstance(m.get("score"), dict) and m["score"].get("ft"))
            and str(m.get("date", "")) >= oggi
            and (limite is None or str(m.get("date", "")) <= limite)
        ]
        if not prossime:
            st.info("Nessuna partita in arrivo nel periodo scelto.")
            return

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

        indice_q = {}
        if ODDS_API_KEY:
            res_q = carica_quote_api(ODDS_API_KEY)
            if res_q["ok"]:
                indice_q = indice_eventi_quote(res_q["odds"])

        righe = []
        for m in prossime:
            t1, t2 = m["team1"], m["team2"]
            if t1 not in modello["forze"] or t2 not in modello["forze"]:
                continue
            l1, l2, _ = gol_attesi(modello, t1, t2, tiri, nome_fd(t1), nome_fd(t2), usa_assenze=True)
            e = esiti_poisson(l1, l2)
            esiti = {"1": e["1"], "X": e["X"], "2": e["2"]}
            migliore = max(esiti, key=esiti.get)
            p = esiti[migliore]
            mkt = None
            mk_full = None
            if indice_q:
                ev_q = evento_da_indice(indice_q, t1, t2)
                if ev_q is not None:
                    pm = prob_mercato(catalogo_da_evento(ev_q, True), "Esito finale 1X2", ["1", "X", "2"])
                    if pm:
                        mkt = pm[0][migliore]
                        mk_full = pm[0]
            righe.append(
                {
                    "Data": str(m.get("date", "")),
                    "Partita": f"{t1} - {t2}",
                    "Esito": migliore,
                    "Prob. esito": round(p, 1),
                    "Mercato %": None if mkt is None else round(mkt, 1),
                    "Scarto": None if mkt is None else round(p - mkt, 1),
                    "Quota equa": round(100 / p, 2),
                    "1": round(e["1"], 1),
                    "X": round(e["X"], 1),
                    "2": round(e["2"], 1),
                    "Over 2.5": round(e["over25"], 1),
                    "Goal": round(e["goal"], 1),
                    "_t1": t1,
                    "_t2": t2,
                    "_mk": mk_full,
                }
            )

        if not righe:
            st.info("Squadre non presenti nel modello.")
            return

        ha_mercato = any(r["Mercato %"] is not None for r in righe)
        if not ha_mercato:
            for r in righe:
                r.pop("Mercato %", None)
                r.pop("Scarto", None)

        chiavi = {
            "Probabilità più alta": ("Prob. esito", True),
            "Scarto dal mercato": ("Scarto", True),
            "Data": ("Data", False),
            "Over 2.5": ("Over 2.5", True),
            "Goal": ("Goal", True),
        }
        colonna, decrescente = chiavi[ordine]
        if colonna == "Scarto" and not ha_mercato:
            colonna = "Prob. esito"

        def _chiave_ordine(r):
            v = r.get(colonna)
            if colonna == "Scarto":
                return abs(v) if v is not None else -1.0
            return v

        righe.sort(key=_chiave_ordine, reverse=decrescente)

        chiave_v = f"{torneo_corrente()}_{stagione_corrente()}"
        vista = st.radio(
            "Vista", ["Schede", "Tabella"], horizontal=True, key=f"riep_vista_{chiave_v}"
        )
        if vista == "Schede":
            tutte = st.checkbox(
                "Mostra tutte le partite", value=False, key=f"riep_tutte_{chiave_v}"
            )
            schede_riepilogo(righe, tutte)
        else:
            st.dataframe(
                pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in righe]),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Prob. esito": st.column_config.ProgressColumn(
                        "Prob. %", format="%.1f", min_value=0, max_value=100
                    ),
                },
            )
        st.caption(
            f"{len(righe)} partite. Tocca l'intestazione di una colonna per "
            "riordinare. Probabilità in %, stime del modello di Poisson: "
            "non sono garanzie. Mercato % = probabilità dello stesso esito ricavata "
            "dalle quote dei bookmaker senza margine; Scarto = modello meno mercato, "
            "in punti."
        )


def mostra_backtest(matches, tab):
    with tab:
        st.subheader("🧪 Backtest del modello")
        st.caption(
            "Il modello rifà le previsioni sulle partite già giocate, usando "
            "solo i dati precedenti a ciascuna partita, e le confronta con "
            "il risultato vero. Usa solo i gol: i tiri in porta sono medie "
            "di stagione e falserebbero la prova."
        )
        giocate = _giocate_ordinate(matches)
        if len(giocate) < 40:
            st.info(
                "Servono almeno 40 partite giocate. Prova con la stagione 2025-26."
            )
            return

        c1, c2 = st.columns(2)
        with c1:
            rodaggio = st.selectbox(
                "Partite di rodaggio",
                [30, 50, 100],
                index=1,
                key=f"bt_rodaggio_{torneo_corrente()}_{stagione_corrente()}",
            )
        with c2:
            d_scelto = st.selectbox(
                "Peso forma recente",
                [1.00, 0.98, 0.95, 0.90],
                index=2,
                format_func=lambda x: "1.00 (nessun peso)" if x == 1.0 else f"{x:.2f}",
                key=f"bt_peso_{torneo_corrente()}_{stagione_corrente()}",
            )
        if len(giocate) < rodaggio + 20:
            st.info("Poche partite dopo il rodaggio: scegli meno rodaggio o un'altra stagione.")
            return

        if not abbastanza_partite(matches, 40):
            st.info("Dati insufficienti per eseguire il backtest.")
            return

        confronto = []
        dettaglio = None
        ris_scelto = None
        pesi = [1.00, 0.98, 0.95, 0.90]
        # (etichetta, d, emivita in giorni): il decadimento per data pesa le
        # partite in base a quanto tempo è passato, non a quante ne sono state giocate.
        configurazioni = [
            ("1.00 (nessun peso)" if d == 1.0 else f"{d:.2f}", d, None) for d in pesi
        ] + [(f"Per data, emivita {g} giorni", 1.0, g) for g in (60, 120, 240)]
        barra = st.progress(0.0, text="Backtest in corso…")
        try:
            for i, (etich, d, emivita) in enumerate(configurazioni):
                barra.progress(
                    i / len(configurazioni),
                    text=f"Backtest {etich} ({i + 1}/{len(configurazioni)})…",
                )
                try:
                    ris = esegui_backtest(
                        matches, torneo_corrente(), stagione_corrente(), d, rodaggio, emivita,
                        firma_dati(matches),
                    )
                    s = riassumi_backtest(ris)
                except Exception as e:  # una configurazione che fallisce non blocca le altre
                    st.warning(f"Backtest «{etich}» non riuscito: {type(e).__name__}.")
                    continue
                if not s:
                    continue
                confronto.append(
                    {
                        "Peso forma": etich,
                        "Partite testate": s["n"],
                        "Esiti azzeccati": f"{s['acc']:.1f}%",
                        "Errore Brier": round(s["brier"], 3),
                    }
                )
                if d == d_scelto and emivita is None:
                    dettaglio = s
                    ris_scelto = ris
            barra.progress(1.0, text="Backtest completato")
        finally:
            barra.empty()
        if not dettaglio:
            st.info("Dati insufficienti per questo torneo.")
            return

        confronto.append(
            {
                "Peso forma": "Riferimento (frequenze di lega)",
                "Partite testate": dettaglio["n"],
                "Esiti azzeccati": f"{dettaglio['acc_base']:.1f}%",
                "Errore Brier": round(dettaglio["brier_base"], 3),
            }
        )
        st.markdown("**Confronto tra impostazioni**")
        st.dataframe(pd.DataFrame(confronto), use_container_width=True, hide_index=True)

        s = dettaglio
        st.markdown(f"**Dettaglio con peso {d_scelto:.2f}** ({s['n']} partite testate)")
        m1, m2 = st.columns(2)
        m1.metric(
            "Esiti 1X2 azzeccati",
            f"{s['acc']:.1f}%",
            delta=f"{s['acc'] - s['acc_base']:+.1f} punti vs riferimento",
        )
        m2.metric(
            "Errore Brier 1X2",
            f"{s['brier']:.3f}",
            delta=f"{s['brier'] - s['brier_base']:+.3f} vs riferimento",
            delta_color="inverse",
        )
        m3, m4 = st.columns(2)
        m3.metric(
            "Over 2.5 azzeccato",
            f"{s['acc_over']:.1f}%",
            delta=f"Brier {s['br_over'] - s['br_over_base']:+.3f}",
            delta_color="inverse",
        )
        m4.metric(
            "Goal azzeccato",
            f"{s['acc_goal']:.1f}%",
            delta=f"Brier {s['br_goal'] - s['br_goal_base']:+.3f}",
            delta_color="inverse",
        )

        st.markdown("**Calibrazione: se dice 60%, succede 6 volte su 10?**")
        st.dataframe(pd.DataFrame(s["fasce"]), use_container_width=True, hide_index=True)
        st.caption(
            "Brier: più basso è meglio, tirare a caso (un terzo per esito) dà "
            "0.667. Il riferimento usa solo le frequenze storiche della lega. "
            "Se il modello non batte il riferimento, non aggiunge informazione. "
            "Con poche centinaia di partite, differenze di uno o due punti "
            "possono essere solo fortuna."
            )
        if ris_scelto:
            _mostra_calibrazione_probabilita(ris_scelto)


def _mostra_calibrazione_probabilita(ris):
    """Adatta le curve di calibrazione sul backtest e le prova fuori campione."""
    st.markdown("---")
    st.markdown("**🎚️ Calibrazione delle probabilità**")
    if st.session_state.get("_msg_calib"):
        st.success(st.session_state.pop("_msg_calib"))
    cal = valore.adatta_calibrazione(ris)
    if not cal:
        st.info("Servono almeno un centinaio di partite testate per calibrare.")
        return
    st.caption(
        f"Le curve si adattano sulle prime {cal['n_fit']} partite testate e si "
        f"misurano sulle ultime {cal['n_test']}, che non hanno mai visto. Si "
        "attivano solo i mercati in cui l'errore Brier scende davvero."
    )
    nomi = {"1x2": "1X2", "over": "Over 2.5", "goal": "Goal"}
    righe = []
    for k, (prima, dopo) in cal["prima_dopo"].items():
        righe.append({
            "Mercato": nomi[k],
            "Brier prima": round(prima, 4),
            "Brier dopo": round(dopo, 4),
            "Esito": "✅ migliora" if cal["utile"][k] else "— nessun vantaggio",
        })
    st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)
    with st.expander("Affidabilità: cosa dice il modello e cosa succede"):
        for k in ("1x2", "over", "goal"):
            t = valore.tabella_affidabilita(ris, k)
            if t:
                st.markdown(f"*{nomi[k]}*")
                st.dataframe(
                    pd.DataFrame([
                        {
                            "Fascia": f"{r['da'] * 100:.0f}-{r['a'] * 100:.0f}%",
                            "Casi": r["n"],
                            "Prob. media": f"{r['prob_media'] * 100:.1f}%",
                            "Frequenza reale": f"{r['freq_reale'] * 100:.1f}%",
                        }
                        for r in t
                    ]),
                    use_container_width=True, hide_index=True,
                )
    if not any(cal["utile"].values()):
        st.info(
            "Il modello è già abbastanza calibrato: nessuna correzione ha "
            "migliorato i risultati fuori campione. Meglio non applicarne."
        )
        return
    if st.button("✅ Usa queste curve per questo torneo", key=f"calib_salva_{torneo_corrente()}"):
        st.session_state.setdefault("calib", {})[torneo_corrente()] = cal
        st.session_state["_attiva_calib"] = True
        st.session_state["_msg_calib"] = (
            "Curve salvate e attivate: consigli, radar e pronostici di questo torneo "
            "ora usano le probabilità calibrate. Puoi spegnerle dalla barra laterale."
        )
        persistenza.salva_se_cambiato()
        st.rerun()
    st.caption(
        "Le curve restano finché l'app è aperta. Con poche centinaia di partite "
        "la correzione può essere rumore: la prova fuori campione serve a questo."
    )


def mostra_ai_advice(tab):
    with tab:
        st.subheader("💡 AI Advice")
        st.caption(
            "Le partite con le previsioni più solide secondo il modello. "
            "Non confronta le quote dei bookmaker, quindi non può dire se "
            "una giocata ha valore: misura solo quanto il modello è sicuro. "
            "Nessuna giocata è garantita. Gioca responsabilmente, solo se "
            "maggiorenne e solo somme che puoi permetterti di perdere."
        )
        c1, c2 = st.columns(2)
        with c1:
            finestra = st.selectbox(
                "Partite in arrivo",
                ["Prossimi 3 giorni", "Prossimi 7 giorni", "Prossimi 14 giorni"],
                index=1,
                key="advice_finestra",
            )
        with c2:
            doppia = st.checkbox(
                "Includi doppia chance (1X, X2)", value=False, key="advice_doppia"
            )

        giorni = int(finestra.split()[1])
        with st.spinner("Analisi di tutti i campionati..."):
            consigli = raccogli_consigli(stagione_corrente(), giorni, doppia)
        guasti = sorted(
            k.split(":")[1]
            for k, v in st.session_state.get("_stato_dati", {}).items()
            if k.startswith("matches:") and k.endswith(f":{stagione_corrente()}")
            and v["stato"] in (ERRORE, OBSOLETO)
        )
        if guasti:
            st.warning(
                "⚠️ Dati non aggiornati per: " + ", ".join(guasti)
                + ". I consigli qui sotto potrebbero essere incompleti."
            )
        if not consigli:
            st.info(
                "Nessuna partita trovata nel periodo. Prova una finestra più "
                "ampia o un'altra stagione."
            )
            return

        top = consigli[:10]
        st.markdown("**Top 10 giocate**")
        righe = [
            {
                "Difficoltà": stelle_difficolta(c["p"]),
                "Partita": c["partita"],
                "Giocata": c["giocata"],
                "Prob. %": round(c["p"], 1),
                "Quota equa": round(100 / c["p"], 2),
                "Data": c["data"],
                "Campionato": c["campionato"],
            }
            for c in top
        ]
        st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)
        bottone_registra(
            "reg_top10",
            da_consigli(top, stagione_corrente()),
            "AI Advice",
            "📌 Registra le Top 10 nel registro pronostici",
        )

        st.markdown("**Multiple**")
        schemi = [("Doppia", 2), ("Tripla", 3), ("Quintupla", 5)]
        for nome, k in schemi:
            # una gamba per partita: due giocate sulla stessa gara non sono
            # indipendenti e il prodotto delle probabilità sarebbe sbagliato
            gambe = valore.gambe_indipendenti(consigli, k)
            if len(gambe) < k:
                continue
            prob = 1.0
            for g in gambe:
                prob *= g["p"] / 100
            testo = f"**{nome}** - {stelle_multipla(prob * 100)}  \n"
            testo += (
                f"Probabilità combinata **{prob * 100:.1f}%**, "
                f"quota equa **{1 / prob:.2f}**  \n"
            )
            for g in gambe:
                testo += f"• {g['partita']}: {g['giocata']} ({g['p']:.1f}%)  \n"
            st.markdown(testo)

        st.caption(
            "La probabilità di una multipla è il prodotto di quelle delle "
            "singole giocate, quindi scende in fretta. La quota equa non "
            "include il margine del bookmaker: le quote reali sono più basse. "
            "Le stelle indicano la difficoltà: più sono, meno è probabile. "
            "Ogni multipla ha una sola gamba per partita."
        )
        if st.session_state.get("usa_calib") and st.session_state.get("calib"):
            st.caption(
                "Probabilità calibrate attive per: "
                + ", ".join(sorted(st.session_state["calib"])) + "."
            )
        coperti = sorted({c["campionato"] for c in consigli})
        st.caption("Campionati con dati: " + ", ".join(coperti) + ".")


def sezione_confronto(matches):
    oggi = adesso().strftime("%Y-%m-%d")
    prossime = [
        m
        for m in matches
        if isinstance(m, dict)
        and m.get("team1")
        and m.get("team2")
        and str(m.get("date", "")) >= oggi
    ]

    if not prossime:
        st.info("Nessuna partita futura disponibile per questo torneo/stagione.")
        return

    match_dict = {
        f"{m.get('date', 'Data n.d.')} | {m['team1']} vs {m['team2']}": m
        for m in prossime
    }

    st.markdown("🎯 *Seleziona una partita per il Confronto Diretto e Pronostico IA:*")
    scelta = st.selectbox(
        "Seleziona la Partita della Giornata",
        list(match_dict.keys()),
        key=f"match_scelto_{torneo_corrente()}_{stagione_corrente()}",
    )

    m_sel = match_dict[scelta]
    t1, t2 = m_sel["team1"], m_sel["team2"]

    stats_t1 = calcola_statistiche_squadra(matches, t1)
    stats_t2 = calcola_statistiche_squadra(matches, t2)
    
    prob_1, prob_x, prob_2, dettagli_v2 = probabilita_v2(matches, t1, t2, stats_t1, stats_t2)
    mostra_grafici_partita(
        t1, t2, stats_t1, stats_t2, prob_1, prob_x, prob_2, dettagli_v2,
        quando=f"{m_sel.get('date', '')} {m_sel.get('time', '')}".strip(),
    )
    mostra_dna_pronostico(t1, t2, dettagli_v2)
    st.markdown("---")
    st.markdown(f"### ⚔️ Confronto Diretto: {t1} vs {t2}")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        mostra_metriche_squadra(f"#### 🏠 {badge_squadra(t1)} {t1}", stats_t1)
    with col_s2:
        mostra_metriche_squadra(f"#### ✈️ {badge_squadra(t2)} {t2}", stats_t2)
    mostra_scontri_diretti(torneo_corrente(), t1, t2)
    mostra_grafico_forma({t1: stats_t1, t2: stats_t2})
    mostra_stats_tempi(f"#### ⏱️ Gol per tempo: {t1}", calcola_stats_tempi(matches, t1))
    mostra_stats_tempi(f"#### ⏱️ Gol per tempo: {t2}", calcola_stats_tempi(matches, t2))
    mostra_stats_extra(f"#### 📊 Angoli e tiri: {t1}", t1)
    mostra_stats_extra(f"#### 📊 Angoli e tiri: {t2}", t2)
    mostra_quote_confronto(t1, t2, dettagli_v2)
    mostra_pronostico_v2(matches, t1, t2)
    st.markdown("---")
    analisi = genera_analisi_v2(t1, t2, prob_1, prob_x, prob_2, dettagli_v2)
    st.markdown(
        f"<div class='ai-box'>{analisi}<br><br><b>Previsioni Esito 1X2:</b><br>"
        f"• {t1} (1): <b>{prob_1}%</b><br>"
        f"• Pareggio (X): <b>{prob_x}%</b><br>"
        f"• {t2} (2): <b>{prob_2}%</b></div>",
        unsafe_allow_html=True,
        )


def pagina_dashboard():
    col_title, col_home_btn = st.columns([0.80, 0.20])
    with col_title:
        st.title("⚽ b-betting")
        st.markdown(
    "<p style='color:#8b949e; font-size:14px; margin-top:-10px;'>"
    "Football Statistics • Analysis • Probabilities"
    "</p>",
    unsafe_allow_html=True,
        )
    with col_home_btn:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🏠 Home", use_container_width=True, help="Torna alla Home"):
            st.session_state.pagina = "home"
            st.rerun()

    st.divider()

    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; padding: 25px; border-radius: 16px; margin-bottom: 20px;'>
            <h2 style='color: #58a6ff; margin-bottom: 5px;'>⚽ b-betting Hub</h2>
            <p style='color: #8b949e; font-size: 14px; margin-top: 0;'>Piattaforma avanzata di Live Data Architecture, Statistiche Sportive e Previsioni Algoritmiche.</p>
            <div style='display: flex; gap: 10px; flex-wrap: wrap; margin-top: 15px;'>
                <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>⚡ Engine: <b>Attivo</b></span>
                <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>📊 Versione: <b>b-betting 0.3.0</b></span>
                <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>🕒 Dati: <b>cache 30 min</b></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.spinner(f"Carico i dati di {torneo_corrente()}…"):
        data = carica_dati_campionato(torneo_corrente(), stagione_corrente())
    matches = data.get("matches", [])
    if data.get("stato") == ERRORE:
        st.error(f"❌ {data['messaggio']}")
    elif data.get("messaggio"):
        st.warning(f"⚠️ {data['messaggio']}")
    elif data.get("scaricato_alle"):
        st.caption(f"Dati scaricati il {data['scaricato_alle']} (cache 30 min).")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(
        ["📅 Palinsesto", "📊 Classifica", "📈 Analisi Match & Statistiche", "🎯 Riepilogo", "🧪 Backtest", "💡 AI Advice", "🧾 Schedina", "💰 Quote Prepartita", "📡 Radar valore"]
    )
    with sezione_sicura("Riepilogo", tab4):
        mostra_riepilogo(matches, tab4)
    with sezione_sicura("Backtest", tab5):
        mostra_backtest(matches, tab5)
    with sezione_sicura("Backtest mercato", tab5):
        mostra_backtest_mercato(matches, tab5)
    with sezione_sicura("AI Advice", tab6):
        mostra_ai_advice(tab6)
    with sezione_sicura("Schedina", tab7):
        mostra_schedina(tab7, matches)
    with sezione_sicura("Quote prepartita", tab8):
        mostra_quote_prepartita(tab8, matches)
    with sezione_sicura("Radar valore", tab9):
        mostra_radar_valore(matches, tab9)
    with sezione_sicura("Palinsesto", tab1):
        st.subheader("Palinsesto Match")
        partite = [m for m in matches if isinstance(m, dict)]
        if partite:
            giornate = []
            for m in partite:
                g = m.get("round")
                if g and g not in giornate:
                    giornate.append(g)

            oggi_p = adesso().strftime("%Y-%m-%d")
            chiave_p = f"{torneo_corrente()}_{stagione_corrente()}"
            filtro = "Tutte le giornate"
            solo_future = False
            if giornate:
                # di default si parte dalla prossima giornata da giocare
                indice = 0
                for i, g in enumerate(giornate):
                    if any(
                        m.get("round") == g and str(m.get("date") or "")[:10] >= oggi_p
                        for m in partite
                    ):
                        indice = i + 1
                        break
                filtro = st.selectbox(
                    "Filtra per giornata",
                    ["Tutte le giornate"] + giornate,
                    index=indice,
                    key=f"filtro_giornata_{chiave_p}",
                )
            else:
                vista_p = st.radio(
                    "Mostra",
                    ["Prossime partite", "Tutte"],
                    horizontal=True,
                    key=f"palinsesto_vista_{chiave_p}",
                )
                solo_future = vista_p == "Prossime partite"

            lista = []
            for m in partite:
                if filtro != "Tutte le giornate" and m.get("round") != filtro:
                    continue
                if solo_future and str(m.get("date") or "")[:10] < oggi_p:
                    continue
                sc = m.get("score")
                ft = sc.get("ft") if isinstance(sc, dict) else None
                lista.append(
                    {
                        "Giornata": m.get("round", ""),
                        "Data": m.get("date", ""),
                        "Casa": m.get("team1", ""),
                        "Ospite": m.get("team2", ""),
                        "Risultato": f"{ft[0]}-{ft[1]}" if ft else "-",
                    }
                )
            st.dataframe(
                pd.DataFrame(lista), use_container_width=True, hide_index=True
            )
        else:
            st.warning("Dati non disponibili per questo torneo.")

    with sezione_sicura("Classifica", tab2):
        st.subheader("Classifica Live")
        classifica = {}
        for m in matches:
            if (
                isinstance(m, dict)
                and isinstance(m.get("score"), dict)
                and m["score"].get("ft")
            ):
                t1, t2 = m.get("team1"), m.get("team2")
                if not t1 or not t2:
                    continue
                g1, g2 = m["score"]["ft"][0], m["score"]["ft"][1]
                for sq in (t1, t2):
                    if sq not in classifica:
                        classifica[sq] = {
                            "Squadra": sq,
                            "PG": 0,
                            "Pt": 0,
                            "GF": 0,
                            "GS": 0,
                        }
                classifica[t1]["PG"] += 1
                classifica[t2]["PG"] += 1
                classifica[t1]["GF"] += g1
                classifica[t1]["GS"] += g2
                classifica[t2]["GF"] += g2
                classifica[t2]["GS"] += g1
                if g1 > g2:
                    classifica[t1]["Pt"] += 3
                elif g1 < g2:
                    classifica[t2]["Pt"] += 3
                else:
                    classifica[t1]["Pt"] += 1
                    classifica[t2]["Pt"] += 1

        if classifica:
            df_c = pd.DataFrame(list(classifica.values()))
            df_c["DR"] = df_c["GF"] - df_c["GS"]
            df_c = df_c.sort_values(
                by=["Pt", "DR"], ascending=False
            ).reset_index(drop=True)
            df_c.index += 1
            st.dataframe(df_c, use_container_width=True)
        else:
            st.warning("Classifica non disponibile.")

    with sezione_sicura("Analisi Match & Statistiche", tab3):
        st.subheader("📊 Analisi Match & Statistiche")

        tutte_squadre = sorted(
            {m.get("team1") for m in matches if isinstance(m, dict) and m.get("team1")}
            | {m.get("team2") for m in matches if isinstance(m, dict) and m.get("team2")}
        )

        if not tutte_squadre:
            st.warning("Dati non disponibili per questo torneo.")
        else:
            st.markdown("🔍 **Cerca Statistiche per Singola Squadra:**")
            squadra_singola = st.selectbox(
                "Seleziona o digita una squadra per visualizzare le sue statistiche",
                ["-- Seleziona una squadra --"] + tutte_squadre,
                key="ricerca_singola_squadra",
            )

            if squadra_singola != "-- Seleziona una squadra --":
                st.markdown(f"### 📋 Report: {badge_squadra(squadra_singola)} {squadra_singola}", unsafe_allow_html=True)
                stats_singola = calcola_statistiche_squadra(matches, squadra_singola)
                if stats_singola:
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("Punti a Partita (PPG)", stats_singola["ppg"])
                        st.metric("Partite Giocate", stats_singola["tot"])
                    with c2:
                        st.metric("Media Gol Fatti", stats_singola["gf_avg"])
                        st.metric("Over 2.5 %", f"{stats_singola['over_2_5_pct']}%")
                    with c3:
                        st.metric("Media Gol Subiti", stats_singola["gs_avg"])
                        st.metric(
                            "Clean Sheet %", f"{stats_singola['clean_sheets_pct']}%"
                        )
                    with c4:
                        st.metric("BTTS %", f"{stats_singola['btts_pct']}%")

                    st.markdown("**Stato di Forma (Ultime 5):**")
                    classi = {"V": "badge-v", "N": "badge-n", "P": "badge-p"}
                    forma_html = "".join(
                        f"<span class='{classi[r]}'>{r}</span>"
                        for r in stats_singola["forma"][-5:]
                    )
                    st.markdown(forma_html or "N.D.", unsafe_allow_html=True)
                    mostra_stats_tempi("#### ⏱️ Gol per tempo", calcola_stats_tempi(matches, squadra_singola))
                    mostra_grafico_forma({squadra_singola: stats_singola})
                    mostra_stats_extra("#### 📊 Angoli, tiri e disciplina", squadra_singola)
                else:
                    st.info(
                        "Nessun dato di match disputati disponibile per questa"
                        " squadra nella stagione selezionata."
                    )

            st.markdown("---")
            sezione_confronto(matches)

    # Avvisi sulle fonti secondarie (tiri, angoli, cartellini): vanno in fondo
    # perché vengono scaricate mentre i tab si costruiscono.
    mostra_stato_dati(
        [k for k in st.session_state.get("_stato_dati", {})
         if k.startswith("stats:") and f":{torneo_corrente()}:" in k]
    )
