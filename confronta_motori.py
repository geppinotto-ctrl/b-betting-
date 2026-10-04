"""Confronto Poisson vs Dixon–Coles su dati reali, fuori campione.

Uso (dalla cartella del progetto, con streamlit installato):

    python confronta_motori.py                      # Serie A, 3 stagioni
    python confronta_motori.py "Italia - Serie A" 2024-25 2025-26

Per ogni partita (dopo il rodaggio) il modello viene ricalcolato usando SOLO
le partite di giorni precedenti, come fa il tab Backtest. Per Dixon–Coles
vengono provati ρ fissi e un ρ stimato sulla stagione PRECEDENTE (nessuna
informazione dal futuro). Metriche: log-loss e Brier (più basso = meglio).

Si decide di adottare Dixon–Coles solo se batte Poisson in modo coerente
su più stagioni, non su una sola.
"""

import math
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import streamlit as st

import motore_probabilistico as mp
from config import STAGIONI, campionati_disponibili
from dati import carica_dati_campionato
from modello import _giocate_ordinate, calcola_forze, gol_attesi

RODAGGIO = 60
D = 0.95
RHO_FISSI = (-0.15, -0.10, -0.05)


def _partite(gio):
    return [(m["team1"], m["team2"], m["score"]["ft"][0], m["score"]["ft"][1]) for m in gio]


def rho_da_stagione(campionato, stagione):
    """ρ stimato su una stagione intera (da usare per la stagione successiva)."""
    gio = _giocate_ordinate(carica_dati_campionato(campionato, stagione).get("matches", []))
    mod = calcola_forze(gio, d=D)
    if not mod:
        return None
    rho, _ = mp.stima_rho(_partite(gio), mod)
    return rho


def valuta(campionato, stagione, rho_prec):
    gio = _giocate_ordinate(carica_dati_campionato(campionato, stagione).get("matches", []))
    if len(gio) <= RODAGGIO + 20:
        return None
    motori = {"Poisson": None}
    for r in RHO_FISSI:
        motori[f"DC ρ={r:+.2f}"] = r
    if rho_prec is not None:
        motori[f"DC ρ prec.={rho_prec:+.2f}"] = rho_prec

    acc = {nome: {"ll": 0.0, "br": 0.0, "ll_o": 0.0, "ll_g": 0.0, "pX": 0.0} for nome in motori}
    n = 0
    reali_X = 0
    for i in range(RODAGGIO, len(gio)):
        m = gio[i]
        data_i = str(m.get("date", ""))
        storico = [g for g in gio[:i] if str(g.get("date", "")) < data_i]
        mod = calcola_forze(storico, d=D)
        t1, t2 = m["team1"], m["team2"]
        if not mod or t1 not in mod["forze"] or t2 not in mod["forze"]:
            continue
        l1, l2, _ = gol_attesi(mod, t1, t2)
        a, b = m["score"]["ft"][0], m["score"]["ft"][1]
        k = 0 if a > b else (1 if a == b else 2)
        over = 1 if a + b > 2 else 0
        goal = 1 if (a > 0 and b > 0) else 0
        n += 1
        reali_X += k == 1
        for nome, rho in motori.items():
            # ρ=0 coincide esattamente con Poisson e NON dipende dal selettore dell'app
            e = mp.esiti_dixon_coles(l1, l2, rho=0.0 if rho is None else rho)
            p = [e["1"] / 100, e["X"] / 100, e["2"] / 100]
            s = acc[nome]
            s["ll"] += -math.log(max(p[k], 1e-9))
            s["br"] += sum((p[j] - (1 if j == k else 0)) ** 2 for j in range(3))
            po, pg = e["over25"] / 100, e["goal"] / 100
            s["ll_o"] += -math.log(max(po if over else 1 - po, 1e-9))
            s["ll_g"] += -math.log(max(pg if goal else 1 - pg, 1e-9))
            s["pX"] += p[1]
    if n == 0:
        return None
    return n, reali_X / n, {nome: {c: v / n for c, v in s.items()} for nome, s in acc.items()}


def confronta(campionato, stagioni=None):
    """Esegue il confronto e restituisce (blocchi, riepilogo).

    blocchi:   [{'stagione', 'n', 'freq_x', 'tab'}] una voce per stagione
    riepilogo: {motore: (partite, differenza media di log-loss vs Poisson)}
    """
    ordine = list(reversed(STAGIONI))  # dalla più vecchia alla più recente
    scelte = [s for s in ordine if (not stagioni or s in stagioni)]
    blocchi, totale = [], {}
    for st_ in scelte:
        pos = ordine.index(st_)
        rho_prec = rho_da_stagione(campionato, ordine[pos - 1]) if pos > 0 else None
        ris = valuta(campionato, st_, rho_prec)
        if not ris:
            continue
        n, freq_x, tab = ris
        blocchi.append({"stagione": st_, "n": n, "freq_x": freq_x, "tab": tab})
        base = tab["Poisson"]
        for nome, s in tab.items():
            chiave = "DC ρ stimato stag. prec." if "prec" in nome else nome
            totale.setdefault(chiave, []).append((n, s["ll"] - base["ll"]))
    riepilogo = {}
    for nome, lst in totale.items():
        if nome != "Poisson":
            tot_n = sum(x[0] for x in lst)
            riepilogo[nome] = (tot_n, sum(x[0] * x[1] for x in lst) / tot_n)
    return blocchi, riepilogo


@st.cache_data(ttl=3600, show_spinner=False)
def _confronta_cached(campionato):
    return confronta(campionato)


def _giudizio(blocchi, nome):
    """Frase semplice sul vantaggio di un motore DC rispetto a Poisson."""
    diffs = [b["tab"][nome]["ll"] - b["tab"]["Poisson"]["ll"] for b in blocchi if nome in b["tab"]]
    if not diffs:
        return "n/d"
    media = sum(diffs) / len(diffs)
    if all(d < 0 for d in diffs) and media < -0.002:
        return "✅ meglio di Poisson in tutte le stagioni"
    if all(d > 0 for d in diffs):
        return "❌ peggio di Poisson in tutte le stagioni"
    return "➖ nessuna differenza chiara"


def mostra_confronto_motori():
    """Pagina per l'app: confronto Poisson / Dixon–Coles sul torneo scelto."""
    campionato = st.session_state.get("torneo", "Italia - Serie A")
    st.header("🧪 Poisson vs Dixon–Coles")
    st.caption(
        f"{campionato}. Ogni partita è valutata usando solo quelle giocate prima. "
        "Valori più bassi = previsioni migliori."
    )
    if st.button("✖ Chiudi confronto"):
        st.session_state.mostra_confronto = False
        st.rerun()
    with st.spinner("Calcolo in corso, può richiedere qualche minuto..."):
        blocchi, riepilogo = _confronta_cached(campionato)
    if not blocchi:
        st.warning("Dati insufficienti o non disponibili per questo torneo.")
        return
    for b in blocchi:
        st.subheader(f"Stagione {b['stagione']}: {b['n']} partite")
        st.caption(f"Pareggi reali: {b['freq_x'] * 100:.1f}%")
        righe = [
            {
                "Motore": nome,
                "Errore 1X2 (log-loss)": round(s["ll"], 4),
                "Brier": round(s["br"], 4),
                "Errore Over 2.5": round(s["ll_o"], 4),
                "Errore Goal": round(s["ll_g"], 4),
                "Pareggio previsto": f"{s['pX'] * 100:.1f}%",
            }
            for nome, s in b["tab"].items()
        ]
        st.dataframe(pd.DataFrame(righe), hide_index=True, use_container_width=True)
    st.subheader("Verdetto")
    nomi = [n for n in blocchi[-1]["tab"] if n != "Poisson"]
    for nome in nomi:
        st.write(f"**{nome}**: {_giudizio(blocchi, nome)}")
    st.caption(
        "Differenze minime (sotto circa 0.002) sono rumore. Passa a Dixon–Coles "
        "solo se vince in modo coerente su più stagioni."
    )


def main():
    args = sys.argv[1:]
    campionato = args[0] if args and args[0] in campionati_disponibili else "Italia - Serie A"
    stagioni = [a for a in args if a in STAGIONI]
    print(f"\n=== {campionato} — rodaggio {RODAGGIO} partite, decadimento d={D} ===")
    blocchi, riepilogo = confronta(campionato, stagioni)
    if not blocchi:
        print("Dati insufficienti o non disponibili.")
    for b in blocchi:
        print(f"\n--- {b['stagione']}: {b['n']} partite valutate, pareggi reali {b['freq_x'] * 100:.1f}% ---")
        print(f"{'motore':<26}{'logloss1X2':>11}{'Brier':>9}{'logloss O2.5':>14}{'logloss GG':>12}{'X medio':>9}")
        for nome, s in b["tab"].items():
            print(
                f"{nome:<26}{s['ll']:>11.4f}{s['br']:>9.4f}{s['ll_o']:>14.4f}"
                f"{s['ll_g']:>12.4f}{s['pX'] * 100:>8.1f}%"
            )
    print("\n=== Differenza media di log-loss 1X2 rispetto a Poisson (negativo = meglio di Poisson) ===")
    for nome, (n, diff) in riepilogo.items():
        print(f"{nome:<26}{diff:>+9.4f}  su {n} partite")
    print(
        "\nLettura: differenze sotto ~0.002 di log-loss su poche centinaia di partite\n"
        "sono rumore. Adotta Dixon–Coles solo se il segno è lo stesso in tutte le stagioni."
    )


if __name__ == "__main__":
    main()
