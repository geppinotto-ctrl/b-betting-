"""Calibrazione dei parametri del modello, fuori campione.

Il modello usa due parametri che finora non erano mai stati verificati:
  d      peso delle partite vecchie (1.00 = tutte pesano uguale,
         0.90 = conta molto la forma recente). Oggi: 0.95
  prior  quante partite "medie" si mescolano ai dati di ogni squadra
         (più alto = squadre più vicine alla media). Oggi: 4

Per ogni combinazione si ricalcola il modello partita per partita usando
SOLO le partite giocate prima, e si misura l'errore (log-loss 1X2). Il
confronto è accoppiato: ogni variante è valutata sulle stesse partite
della configurazione attuale, e si calcola l'errore statistico della
differenza. Una variante è "meglio" solo se la differenza supera tre
errori standard e vince in tutte le stagioni: altrimenti è rumore.
"""

import math

import numpy as np
import pandas as pd
import streamlit as st

import motore_probabilistico as mp
from config import STAGIONI
from dati import carica_dati_campionato
from modello import _giocate_ordinate, calcola_forze, gol_attesi

RODAGGIO = 60
BASE = (0.95, 4)
GRIGLIA_D = (0.90, 0.93, 0.95, 0.97, 0.99, 1.00)
GRIGLIA_PRIOR = (2, 4, 8)
# Si provano 18 combinazioni: una può sembrare migliore solo per fortuna,
# quindi serve una soglia prudente (3 errori standard) e il successo in
# TUTTE le stagioni.
SOGLIA_SE = 3.0


def _errori_stagione(campionato, stagione, varianti):
    """Per ogni variante, lista degli errori (log-loss) partita per partita."""
    gio = _giocate_ordinate(carica_dati_campionato(campionato, stagione).get("matches", []))
    if len(gio) <= RODAGGIO + 20:
        return None
    out = {v: [] for v in varianti}
    for i in range(RODAGGIO, len(gio)):
        m = gio[i]
        data_i = str(m.get("date", ""))
        storico = [g for g in gio[:i] if str(g.get("date", "")) < data_i]
        t1, t2 = m["team1"], m["team2"]
        a, b = m["score"]["ft"][0], m["score"]["ft"][1]
        k = 0 if a > b else (1 if a == b else 2)
        parziale = {}
        for v in varianti:
            mod = calcola_forze(storico, d=v[0], prior=v[1])
            if not mod or t1 not in mod["forze"] or t2 not in mod["forze"]:
                parziale = None
                break
            l1, l2, _ = gol_attesi(mod, t1, t2)
            # ρ=0 equivale a Poisson ed è indipendente dal selettore dell'app
            e = mp.esiti_dixon_coles(l1, l2, rho=0.0)
            p = [e["1"], e["X"], e["2"]][k] / 100
            parziale[v] = -math.log(max(p, 1e-9))
        if parziale is None:
            continue  # stessa partita esclusa per tutte: confronto accoppiato
        for v in varianti:
            out[v].append(parziale[v])
    return {v: np.array(x) for v, x in out.items()}


def calibra(campionato, stagioni=None):
    """Restituisce {'stagioni', 'n', 'righe'} oppure None se mancano dati."""
    varianti = [(d, p) for d in GRIGLIA_D for p in GRIGLIA_PRIOR]
    ordine = list(reversed(STAGIONI))
    scelte = [s for s in ordine if (not stagioni or s in stagioni)]
    per_stagione = []
    for s in scelte:
        r = _errori_stagione(campionato, s, varianti)
        if r is not None and len(r[BASE]) > 0:
            per_stagione.append((s, r))
    if not per_stagione:
        return None
    base_tutti = np.concatenate([x[BASE] for _, x in per_stagione])
    righe = []
    for v in varianti:
        tutti = np.concatenate([x[v] for _, x in per_stagione])
        diff = tutti - base_tutti
        n = len(diff)
        se = float(diff.std(ddof=1) / math.sqrt(n)) if (n > 1 and v != BASE) else 0.0
        migliori = sum(1 for _, x in per_stagione if x[v].mean() < x[BASE].mean())
        media_diff = float(diff.mean())
        if v == BASE:
            verdetto = "⭐ attuale"
        elif media_diff < -SOGLIA_SE * se and migliori == len(per_stagione):
            verdetto = "✅ meglio"
        elif media_diff > SOGLIA_SE * se:
            verdetto = "❌ peggio"
        else:
            verdetto = "➖ come l'attuale"
        righe.append(
            {
                "d": v[0],
                "prior": v[1],
                "errore": float(tutti.mean()),
                "diff": media_diff,
                "se": se,
                "stagioni_meglio": migliori,
                "verdetto": verdetto,
            }
        )
    return {
        "stagioni": [s for s, _ in per_stagione],
        "n": int(len(base_tutti)),
        "righe": righe,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def _calibra_cached(campionato):
    return calibra(campionato)


def mostra_calibrazione():
    """Pagina per l'app: calibrazione dei parametri sul torneo scelto."""
    campionato = st.session_state.get("torneo", "Italia - Serie A")
    st.header("🎛️ Calibrazione del modello")
    st.caption(
        f"{campionato}. Ogni partita è valutata usando solo quelle giocate prima. "
        "Errore più basso = previsioni migliori."
    )
    if st.button("✖ Chiudi calibrazione"):
        st.session_state.mostra_calibrazione = False
        st.rerun()
    with st.spinner("Calcolo in corso, può richiedere qualche minuto..."):
        ris = _calibra_cached(campionato)
    if not ris:
        st.warning("Dati insufficienti o non disponibili per questo torneo.")
        return
    st.write(
        f"Stagioni usate: **{', '.join(ris['stagioni'])}** — "
        f"**{ris['n']}** partite valutate."
    )
    righe = sorted(ris["righe"], key=lambda r: r["errore"])
    tabella = pd.DataFrame(
        [
            {
                "d (forma recente)": r["d"],
                "prior (verso la media)": r["prior"],
                "Errore 1X2": round(r["errore"], 4),
                "Diff. vs attuale": f"{r['diff']:+.4f}",
                "± errore": f"{r['se']:.4f}",
                "Stagioni migliori": f"{r['stagioni_meglio']}/{len(ris['stagioni'])}",
                "Verdetto": r["verdetto"],
            }
            for r in righe
        ]
    )
    st.dataframe(tabella, hide_index=True, use_container_width=True)
    meglio = [r for r in righe if r["verdetto"] == "✅ meglio"]
    if meglio:
        b = meglio[0]
        st.success(
            f"Una configurazione batte quella attuale in modo statisticamente "
            f"chiaro: d = {b['d']}, prior = {b['prior']}. Controlla che sia "
            "migliore in tutte le stagioni prima di cambiarla."
        )
    else:
        st.info(
            "Nessuna configurazione batte in modo chiaro quella attuale "
            "(d = 0.95, prior = 4): i parametri attuali vanno bene, non cambiare nulla."
        )
    st.caption(
        "d: peso delle partite vecchie (1.00 = tutte uguali, 0.90 = conta molto "
        "la forma recente). prior: partite 'medie' mescolate ai dati di ogni "
        "squadra. Una differenza è reale solo se supera il triplo dell'errore (±) e vale in tutte le stagioni."
    )
