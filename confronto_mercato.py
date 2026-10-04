import math

import pandas as pd
import streamlit as st

from config import stagione_corrente, torneo_corrente
from dati import carica_stats_extra, trova_nome_fd
from modello import _giocate_ordinate, calcola_forze, esiti_poisson, gol_attesi

# (colonna 1, colonna X, colonna 2, nome)
FONTI_RIF = [
    ("PSCH", "PSCD", "PSCA", "Pinnacle (chiusura)"),
    ("AvgCH", "AvgCD", "AvgCA", "Media bookmaker (chiusura)"),
    ("PSH", "PSD", "PSA", "Pinnacle"),
    ("AvgH", "AvgD", "AvgA", "Media bookmaker"),
    ("B365H", "B365D", "B365A", "Bet365"),
]
FONTI_GIOCO = [
    ("AvgH", "AvgD", "AvgA", "Media bookmaker"),
    ("B365H", "B365D", "B365A", "Bet365"),
    ("MaxH", "MaxD", "MaxA", "Migliore quota (ottimistica)"),
]
PESO_MERCATO = 0.5  # lo stesso del Radar valore


def fonti_disponibili(df, elenco):
    """Fonti di quote presenti nel file e con dati nella maggior parte delle partite."""
    out = []
    for h, x, a, nome in elenco:
        if all(c in df.columns for c in (h, x, a)):
            ok = pd.to_numeric(df[h], errors="coerce").notna().mean()
            if ok >= 0.7:
                out.append((h, x, a, nome))
    return out


def _num(v):
    try:
        f = float(v)
        return f if f > 1.0 else None
    except Exception:
        return None


def costruisci_confronto(matches, df, d, rodaggio, cols_rif, cols_gioco):
    """Per ogni partita giocata (dopo il rodaggio): previsione del modello fatta
    con i soli dati precedenti, probabilità del mercato (senza margine) e quote
    di gioco. Ritorna una lista di dizionari."""
    giocate = _giocate_ordinate(matches)
    nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
    mappa = {}

    def fd(t):
        if t not in mappa:
            mappa[t] = trova_nome_fd(t, nomi)
        return mappa[t]

    indice = {}
    for _, r in df.iterrows():
        indice.setdefault((r["HomeTeam"], r["AwayTeam"]), r)

    righe = []
    for i in range(rodaggio, len(giocate)):
        m = giocate[i]
        t1, t2 = m["team1"], m["team2"]
        a, b = m["score"]["ft"][0], m["score"]["ft"][1]
        reale = 0 if a > b else (1 if a == b else 2)
        n1, n2 = fd(t1), fd(t2)
        if not n1 or not n2:
            continue
        riga = indice.get((n1, n2))
        if riga is None:
            continue
        rif = [_num(riga[c]) for c in cols_rif[:3]]
        gio = [_num(riga[c]) for c in cols_gioco[:3]]
        if any(x is None for x in rif) or any(x is None for x in gio):
            continue
        # solo partite di giorni precedenti: quelle dello stesso giorno potrebbero
        # essere finite dopo l'inizio di questa
        data_i = str(m.get("date", ""))
        storico = [g for g in giocate[:i] if str(g.get("date", "")) < data_i]
        modello = calcola_forze(storico, d=d)
        if not modello or t1 not in modello["forze"] or t2 not in modello["forze"]:
            continue
        l1, l2, _ = gol_attesi(modello, t1, t2)
        e = esiti_poisson(l1, l2)
        inv = [1.0 / x for x in rif]
        tot = sum(inv)
        righe.append({
            "data": str(m.get("date", "")),
            "partita": f"{t1} - {t2}",
            "mod": [e["1"] / 100, e["X"] / 100, e["2"] / 100],
            "mkt": [x / tot for x in inv],
            "quote": gio,
            "reale": reale,
        })
    return righe


@st.cache_data(ttl=3600, show_spinner=False)
def _confronto_cached(_matches, _df, campionato, stagione, d, rodaggio, nome_rif, nome_gioco):
    cr = next(f for f in FONTI_RIF if f[3] == nome_rif)
    cg = next(f for f in FONTI_GIOCO if f[3] == nome_gioco)
    return costruisci_confronto(_matches, _df, d, rodaggio, cr, cg)


def _media_se(valori):
    n = len(valori)
    if n == 0:
        return 0.0, 0.0
    m = sum(valori) / n
    if n < 2:
        return m, 0.0
    var = sum((v - m) ** 2 for v in valori) / (n - 1)
    return m, math.sqrt(var / n)


def _brier(p, reale):
    return sum((p[k] - (1.0 if k == reale else 0.0)) ** 2 for k in range(3))


def _log_loss(p, reale):
    return -math.log(min(max(p[reale], 1e-9), 1.0))


def _scommesse(righe, regola, peso, prob_min):
    """Profitti (puntata 1) degli esiti che soddisfano la regola."""
    out = []
    for r in righe:
        for k in range(3):
            q, pm, pk = r["quote"][k], r["mod"][k], r["mkt"][k]
            pru = (1 - peso) * pm + peso * pk
            ev_m, ev_p = pm * q - 1, pru * q - 1
            ok = False
            if regola == "tutti":
                ok = True
            elif pm * 100 >= prob_min and pm > pk:
                if regola == "ev_modello":
                    ok = ev_m > 0
                elif regola == "ev_pru_0":
                    ok = ev_p > 0
                elif regola == "ev_pru_5":
                    ok = ev_p > 0.05
                elif regola == "ev_pru_10":
                    ok = ev_p > 0.10
            if ok:
                out.append(((q - 1.0) if k == r["reale"] else -1.0))
    return out


def riassumi_confronto(righe, prob_min=20.0, peso=PESO_MERCATO):
    n = len(righe)
    if n == 0:
        return None
    bm = [_brier(r["mod"], r["reale"]) for r in righe]
    bk = [_brier(r["mkt"], r["reale"]) for r in righe]
    diff = [a - b for a, b in zip(bm, bk)]  # >0: il modello sbaglia di più
    d_media, d_se = _media_se(diff)
    acc_m = sum(1 for r in righe if max(range(3), key=lambda k: r["mod"][k]) == r["reale"]) / n * 100
    acc_k = sum(1 for r in righe if max(range(3), key=lambda k: r["mkt"][k]) == r["reale"]) / n * 100

    pesi = []
    for w in (0.0, 0.25, 0.5, 0.75, 1.0):  # w = peso del mercato
        v = [
            _brier([(1 - w) * r["mod"][k] + w * r["mkt"][k] for k in range(3)], r["reale"])
            for r in righe
        ]
        pesi.append((w, sum(v) / n))

    regole = [
        ("tutti", "Tutti gli esiti (costo del margine)"),
        ("ev_modello", "Filtro Radar + EV modello > 0"),
        ("ev_pru_0", "Filtro Radar + EV prudente > 0"),
        ("ev_pru_5", "Filtro Radar + EV prudente > 5%"),
        ("ev_pru_10", "Filtro Radar + EV prudente > 10%"),
    ]
    scommesse = []
    for chiave, nome in regole:
        prof = _scommesse(righe, chiave, peso, prob_min)
        m, se = _media_se(prof)
        scommesse.append({
            "chiave": chiave, "nome": nome, "n": len(prof),
            "vinte": sum(1 for p in prof if p > 0),
            "roi": m * 100, "se": se * 100,
        })
    ll_mod = sum(_log_loss(r["mod"], r["reale"]) for r in righe) / n
    ll_mkt = sum(_log_loss(r["mkt"], r["reale"]) for r in righe) / n
    return {
        "n": n,
        "ll_mod": ll_mod, "ll_mkt": ll_mkt,
        "brier_mod": sum(bm) / n, "brier_mkt": sum(bk) / n,
        "diff": d_media, "diff_se": d_se,
        "acc_mod": acc_m, "acc_mkt": acc_k,
        "pesi": pesi, "scommesse": scommesse,
    }


def verdetto_brier(s):
    diff, se = s["diff"], s["diff_se"]
    if se > 0 and abs(diff) < 2 * se:
        return ("info",
                f"Differenza di precisione non significativa: il modello sbaglia in media "
                f"{diff:+.4f} rispetto al mercato (errore standard {se:.4f}). Con "
                f"{s['n']} partite non si può dire chi sia più preciso.")
    if diff > 0:
        return ("warning",
                f"Il mercato è più preciso del modello: errore Brier più basso di "
                f"{diff:.4f} (circa {diff / se:.1f} errori standard). Il modello, da solo, "
                f"aggiunge poco rispetto alle quote.")
    return ("success",
            f"Il modello è risultato più preciso del mercato di {-diff:.4f} (circa "
            f"{-diff / se:.1f} errori standard) su queste partite. Resta da confermare "
            f"su altre stagioni prima di fidarsi.")


def verdetto_scommesse(riga):
    if riga["n"] < 30:
        return f"Solo {riga['n']} scommesse: troppe poche per trarre conclusioni."
    lo, hi = riga["roi"] - 2 * riga["se"], riga["roi"] + 2 * riga["se"]
    if hi < 0:
        return (f"ROI {riga['roi']:+.1f}% su {riga['n']} scommesse, chiaramente negativo "
                f"(intervallo {lo:+.1f}% / {hi:+.1f}%).")
    if lo > 0:
        return (f"ROI {riga['roi']:+.1f}% su {riga['n']} scommesse, positivo anche tenendo "
                f"conto dell'incertezza (intervallo {lo:+.1f}% / {hi:+.1f}%). Verifica su "
                f"altre stagioni: una sola stagione può essere fortuna.")
    return (f"ROI {riga['roi']:+.1f}% su {riga['n']} scommesse, ma l'intervallo "
            f"({lo:+.1f}% / {hi:+.1f}%) comprende lo zero: i dati non bastano a dire se "
            f"la regola funzioni.")


def mostra_backtest_mercato(matches, tab):
    with tab:
        st.divider()
        st.subheader("📊 Modello contro mercato")
        st.caption(
            "Rifà le previsioni sulle partite già giocate usando solo i dati precedenti "
            "e le confronta con le quote storiche dei bookmaker (football-data.co.uk). "
            "Dice se il modello aggiunge qualcosa rispetto alle quote e come sarebbero "
            "andate le regole del Radar valore. Usa solo i gol, senza i tiri in porta."
        )
        camp, stag = torneo_corrente(), stagione_corrente()
        df = carica_stats_extra(camp, stag)
        if df is None:
            st.info(
                "Quote storiche disponibili solo per Serie A, Premier League, La Liga, "
                "Bundesliga e Ligue 1, e solo per le stagioni con dati. Prova la 2025-26."
            )
            return
        riferimenti = fonti_disponibili(df, FONTI_RIF)
        giochi = fonti_disponibili(df, FONTI_GIOCO)
        if not riferimenti or not giochi:
            st.info("Questa stagione non contiene quote storiche utilizzabili.")
            return
        if len(_giocate_ordinate(matches)) < 80:
            st.info("Servono almeno 80 partite giocate: prova con la stagione 2025-26.")
            return

        chiave = f"{camp}_{stag}"
        c1, c2 = st.columns(2)
        with c1:
            rodaggio = st.selectbox(
                "Partite di rodaggio", [30, 50, 100], index=1, key=f"cm_rod_{chiave}"
            )
            nome_gioco = st.selectbox(
                "Quote per le scommesse simulate",
                [g[3] for g in giochi],
                key=f"cm_gioco_{chiave}",
            )
        with c2:
            d = st.selectbox(
                "Peso forma recente",
                [1.00, 0.98, 0.95, 0.90],
                index=2,
                format_func=lambda x: "1.00 (nessun peso)" if x == 1.0 else f"{x:.2f}",
                key=f"cm_d_{chiave}",
            )
            prob_min = st.selectbox(
                "Probabilità minima modello %", [15, 20, 25], index=1, key=f"cm_pm_{chiave}"
            )
        nome_rif = riferimenti[0][3]

        with st.spinner("Calcolo in corso..."):
            righe = _confronto_cached(matches, df, camp, stag, d, rodaggio, nome_rif, nome_gioco)
        if len(righe) < 60:
            st.info(
                f"Solo {len(righe)} partite con previsione e quote: poche per un confronto "
                "affidabile. Prova con meno rodaggio o un'altra stagione."
            )
            return
        s = riassumi_confronto(righe, float(prob_min))

        st.markdown("**Precisione delle previsioni 1X2**")
        m1, m2, m3 = st.columns(3)
        m1.metric("Partite confrontate", s["n"])
        m2.metric("Errore Brier modello", f"{s['brier_mod']:.4f}")
        m3.metric(
            f"Errore Brier mercato", f"{s['brier_mkt']:.4f}",
            delta=f"{s['brier_mkt'] - s['brier_mod']:+.4f} vs modello", delta_color="off",
        )
        tipo, testo = verdetto_brier(s)
        getattr(st, tipo)(testo)
        st.caption(
            f"Mercato di riferimento: {nome_rif}, con il margine tolto. Esiti azzeccati: "
            f"modello {s['acc_mod']:.1f}%, mercato {s['acc_mkt']:.1f}%. Log-loss: modello "
            f"{s['ll_mod']:.3f}, mercato {s['ll_mkt']:.3f}. Brier e log-loss più bassi sono "
            "meglio; tirare a caso dà Brier 0.667 e log-loss 1.099."
        )

        st.markdown("**Conviene mescolare modello e mercato?**")
        migliore = min(s["pesi"], key=lambda x: x[1])
        st.dataframe(
            pd.DataFrame([
                {
                    "Peso del mercato": f"{int(w * 100)}%" + (" (solo modello)" if w == 0 else (" (solo mercato)" if w == 1 else "")),
                    "Errore Brier": round(b, 4),
                    "Migliore": "◀" if (w, b) == migliore else "",
                }
                for w, b in s["pesi"]
            ]),
            use_container_width=True, hide_index=True,
        )
        st.caption(
            "L'EV prudente del Radar usa il 50%. Se la riga migliore è vicina al 100%, "
            "il modello da solo non aggiunge informazione."
        )

        st.markdown("**Scommesse simulate con le regole del Radar (1 € ciascuna)**")
        st.dataframe(
            pd.DataFrame([
                {
                    "Regola": r["nome"],
                    "Scommesse": r["n"],
                    "Vinte": r["vinte"],
                    "ROI %": round(r["roi"], 1),
                    "Intervallo (±2 err. std)": (
                        f"{r['roi'] - 2 * r['se']:+.1f} / {r['roi'] + 2 * r['se']:+.1f}"
                        if r["n"] > 1 else "—"
                    ),
                }
                for r in s["scommesse"]
            ]),
            use_container_width=True, hide_index=True,
        )
        radar = next(r for r in s["scommesse"] if r["chiave"] == "ev_pru_0")
        st.info("Regola base del Radar (EV prudente > 0): " + verdetto_scommesse(radar))
        st.caption(
            f"Quote usate per le scommesse: {nome_gioco}. ROI = guadagno medio per euro "
            "puntato. La prima riga mostra quanto costa scommettere su tutto: è il "
            "margine dei bookmaker. Le regole sono quelle del Radar, fissate prima di "
            "guardare i risultati, per non adattarle a questa stagione. Il passato non "
            "garantisce il futuro."
        )
