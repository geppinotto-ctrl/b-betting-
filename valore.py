"""Logica pura per valore, calibrazione e gestione del rischio.

Nessuna dipendenza da Streamlit: tutto qui si può testare con i numeri.

Contenuto:
  * calibrazione isotonica delle probabilità (1X2, Over 2.5, Goal), con prova
    fuori campione: la curva si usa solo se migliora l'errore su partite che
    non ha mai visto;
  * valore atteso (EV) e stake di Kelly frazionato con tetto;
  * closing line value (CLV) sull'archivio schedine;
  * avvisi sulle multiple con gambe correlate (stessa partita).
"""

from itertools import combinations

# ------------------------------------------------------------------
# Calibrazione isotonica
# ------------------------------------------------------------------


def isotonica(punti):
    """Regressione isotonica (pool-adjacent-violators).

    ``punti``: lista di (p_prevista, esito 0/1). Ritorna una curva
    ``{"x": [...], "y": [...]}`` monotona crescente, da usare con
    ``applica_curva``. Con meno di 2 punti ritorna None.
    """
    pts = sorted((float(p), float(y)) for p, y in punti)
    if len(pts) < 2:
        return None
    # punti con la stessa previsione = un solo punto pesato (altrimenti la
    # curva avrebbe gradini verticali impossibili da interpolare)
    gruppi = []
    for x, y in pts:
        if gruppi and gruppi[-1][0] == x:
            gruppi[-1][1] += y
            gruppi[-1][2] += 1.0
        else:
            gruppi.append([x, y, 1.0])
    if len(gruppi) < 2:
        return None
    # blocchi: [somma_y, peso, somma_x pesata]
    blocchi = []
    for x, sy, w in gruppi:
        blocchi.append([sy, w, x * w])
        while len(blocchi) > 1 and (
            blocchi[-2][0] / blocchi[-2][1] > blocchi[-1][0] / blocchi[-1][1]
        ):
            b = blocchi.pop()
            blocchi[-1][0] += b[0]
            blocchi[-1][1] += b[1]
            blocchi[-1][2] += b[2]
    xs = [b[2] / b[1] for b in blocchi]
    ys = [b[0] / b[1] for b in blocchi]
    return {"x": xs, "y": ys}


def applica_curva(p, curva):
    """Probabilità calibrata (0-1) per ``p`` (0-1), con interpolazione lineare."""
    if not curva or not curva.get("x"):
        return p
    xs, ys = curva["x"], curva["y"]
    if p <= xs[0]:
        return ys[0]
    if p >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if p <= xs[i]:
            span = xs[i] - xs[i - 1]
            if span <= 0:
                return ys[i]
            t = (p - xs[i - 1]) / span
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return ys[-1]


def _brier(ps, ys):
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / max(len(ps), 1)


def _serie(ris):
    """Estrae dal backtest le serie (previsione, esito) per ogni mercato."""
    serie = {"1": ([], []), "X": ([], []), "2": ([], []),
             "over": ([], []), "goal": ([], [])}
    for r in ris:
        p, reale = r["p"], r["reale"]
        for k, nome in enumerate(("1", "X", "2")):
            serie[nome][0].append(p[k])
            serie[nome][1].append(1 if reale == k else 0)
        serie["over"][0].append(r["p_over"])
        serie["over"][1].append(r["over"])
        serie["goal"][0].append(r["p_goal"])
        serie["goal"][1].append(r["goal"])
    return serie


def _brier_1x2(ris, curve=None):
    tot = 0.0
    for r in ris:
        ps = list(r["p"])
        if curve:
            ps = [applica_curva(ps[k], curve.get(n)) for k, n in enumerate(("1", "X", "2"))]
            s = sum(ps) or 1.0
            ps = [x / s for x in ps]
        tot += sum((ps[k] - (1 if r["reale"] == k else 0)) ** 2 for k in range(3))
    return tot / max(len(ris), 1)


def adatta_calibrazione(ris, quota_fit=0.7, minimo=60):
    """Adatta le curve sul backtest e le prova fuori campione.

    ``ris`` è la lista cronologica di ``esegui_backtest``. Le curve si
    adattano sul primo ``quota_fit`` delle partite e si misurano sul resto;
    se l'errore non scende, ``utile`` è False e l'app NON le applica.
    Le curve finali (da usare davvero) sono riadattate su tutti i dati.
    """
    n = len(ris)
    if n < minimo:
        return None
    taglio = int(n * quota_fit)
    fit, test = ris[:taglio], ris[taglio:]
    if len(fit) < 30 or len(test) < 15:
        return None

    def curve_da(dati):
        s = _serie(dati)
        return {k: isotonica(list(zip(*s[k]))) for k in s}

    prova = curve_da(fit)
    out = {}
    out["1x2"] = (_brier_1x2(test), _brier_1x2(test, prova))
    s_t = _serie(test)
    for nome in ("over", "goal"):
        ps, ys = s_t[nome]
        dopo = [applica_curva(p, prova[nome]) for p in ps]
        out[nome] = (_brier(ps, ys), _brier(dopo, ys))
    finali = curve_da(ris)
    return {
        "curve": finali,
        "n_fit": len(fit),
        "n_test": len(test),
        "prima_dopo": out,
        # richiede un miglioramento reale, non un pareggio per arrotondamento
        "utile": {k: v[1] < v[0] - 1e-4 for k, v in out.items()},
    }


def calibra_esiti(e, curve, utile=None):
    """Copia di ``e`` (dizionario di ``esiti_poisson``, valori in %) calibrata.

    ``utile``: {"1x2": bool, "over": bool, "goal": bool}; i mercati non utili
    restano com'erano. 1X2 viene rinormalizzato a 100.
    """
    if not curve:
        return dict(e)
    utile = utile or {"1x2": True, "over": True, "goal": True}
    nuovo = dict(e)
    if utile.get("1x2") and all(curve.get(k) for k in ("1", "X", "2")):
        c = {k: applica_curva(e[k] / 100, curve[k]) for k in ("1", "X", "2")}
        s = sum(c.values())
        if s > 0:
            for k in ("1", "X", "2"):
                nuovo[k] = c[k] / s * 100
    if utile.get("over") and curve.get("over"):
        p = min(max(applica_curva(e["over25"] / 100, curve["over"]), 0.0), 1.0)
        nuovo["over25"], nuovo["under25"] = p * 100, (1 - p) * 100
    if utile.get("goal") and curve.get("goal"):
        p = min(max(applica_curva(e["goal"] / 100, curve["goal"]), 0.0), 1.0)
        nuovo["goal"], nuovo["nogoal"] = p * 100, (1 - p) * 100
    return nuovo


def tabella_affidabilita(ris, mercato="1x2", fasce=(0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.01)):
    """Righe (fascia, n, prob. media, frequenza reale) per il grafico di affidabilità."""
    s = _serie(ris)
    if mercato == "1x2":
        ps = s["1"][0] + s["X"][0] + s["2"][0]
        ys = s["1"][1] + s["X"][1] + s["2"][1]
    else:
        ps, ys = s[mercato]
    righe = []
    for lo, hi in zip(fasce[:-1], fasce[1:]):
        dentro = [(p, y) for p, y in zip(ps, ys) if lo <= p < hi]
        if dentro:
            righe.append({
                "da": lo, "a": min(hi, 1.0), "n": len(dentro),
                "prob_media": sum(p for p, _ in dentro) / len(dentro),
                "freq_reale": sum(y for _, y in dentro) / len(dentro),
            })
    return righe


# ------------------------------------------------------------------
# Valore atteso e Kelly
# ------------------------------------------------------------------


def ev(p_pct, quota):
    """Valore atteso per 1 € puntato, con ``p_pct`` in percentuale."""
    return p_pct / 100 * quota - 1


def kelly_frazionato(p_pct, quota, frazione=0.25, tetto=0.05):
    """Quota di bankroll da puntare (0-1): Kelly pieno × ``frazione``, al massimo ``tetto``.

    Con EV <= 0 ritorna 0: non si punta mai senza vantaggio.
    """
    if quota <= 1.0:
        return 0.0
    p = p_pct / 100
    f = (p * quota - 1) / (quota - 1)
    if f <= 0:
        return 0.0
    return min(f * frazione, tetto)


def stake_giornaliero(righe, bankroll, frazione=0.25, tetto_singola=0.05, tetto_giornata=0.15):
    """Assegna a ogni riga ``{"p": %, "quota": q}`` uno stake in euro.

    Se la somma supera ``tetto_giornata`` del bankroll, tutti gli stake si
    riducono in proporzione. Aggiunge le chiavi ``frac`` e ``stake``.
    """
    out = []
    for r in righe:
        f = kelly_frazionato(r["p"], r["quota"], frazione, tetto_singola)
        out.append({**r, "frac": f})
    tot = sum(r["frac"] for r in out)
    scala = min(1.0, tetto_giornata / tot) if tot > 0 else 1.0
    for r in out:
        r["frac"] *= scala
        r["stake"] = round(bankroll * r["frac"], 2)
    return out


def punteggio_valore(p_pct, quota, peso_mercato=0.5, p_mkt_pct=None):
    """Chiave di ordinamento per le giocate: EV con probabilità prudente.

    Se manca la probabilità del mercato si usa quella del modello.
    """
    p = p_pct if p_mkt_pct is None else (1 - peso_mercato) * p_pct + peso_mercato * p_mkt_pct
    return ev(p, quota)


# ------------------------------------------------------------------
# Closing line value
# ------------------------------------------------------------------


def clv_pct(quota_presa, quota_chiusura):
    """CLV in % (positivo = hai preso una quota migliore di quella di chiusura)."""
    try:
        qp, qc = float(quota_presa), float(quota_chiusura)
    except (TypeError, ValueError):
        return None
    if qp <= 1.0 or qc <= 1.0:
        return None
    return (qp / qc - 1) * 100


def statistiche_clv(arch):
    """Media del CLV sulle selezioni dell'archivio che hanno ``quota_chiusura``."""
    valori = []
    for a in arch:
        for e in a.get("eventi", []) or []:
            c = clv_pct(e.get("quota"), e.get("quota_chiusura"))
            if c is not None:
                valori.append(c)
    if not valori:
        return {"n": 0, "medio": 0.0, "positivi_pct": 0.0}
    return {
        "n": len(valori),
        "medio": sum(valori) / len(valori),
        "positivi_pct": sum(1 for v in valori if v > 0) / len(valori) * 100,
    }


# ------------------------------------------------------------------
# Multiple correlate
# ------------------------------------------------------------------


def _partita_base(etichetta):
    """'Inter - Milan (2026-10-05)' -> 'Inter - Milan'."""
    return str(etichetta).split(" (")[0].strip()


def _famiglia(giocata):
    g = str(giocata).lower()
    if g.startswith("1x2") or g in ("1x", "x2", "12"):
        return "esito"
    if "over" in g or "under" in g:
        return "gol_totali"
    if "goal" in g:
        return "goal"
    return "altro"


def avvisi_correlazione(righe):
    """Avvisi per le gambe della stessa partita.

    ``righe``: lista di dizionari con ``Partita`` e ``Giocata``. Tra gambe
    della stessa partita le probabilità non sono indipendenti: moltiplicare le
    quote sovrastima o sottostima la vincita reale. Il bookmaker di solito
    rifiuta o ricalcola queste combinazioni.
    """
    per_partita = {}
    for r in righe:
        per_partita.setdefault(_partita_base(r["Partita"]), []).append(r["Giocata"])
    avvisi = []
    for partita, gio in per_partita.items():
        if len(gio) < 2:
            continue
        fam = [_famiglia(g) for g in gio]
        dettagli = []
        for (a, fa), (b, fb) in combinations(zip(gio, fam), 2):
            if {fa, fb} == {"esito", "gol_totali"}:
                dettagli.append(f"«{a}» e «{b}»: l'esito e i gol totali si influenzano")
            elif {fa, fb} == {"goal", "gol_totali"}:
                dettagli.append(f"«{a}» e «{b}»: Goal e Over/Under sono molto legati")
            elif fa == fb:
                dettagli.append(f"«{a}» e «{b}»: stesso tipo di mercato sulla stessa partita")
        avvisi.append({
            "partita": partita,
            "giocate": gio,
            "dettagli": dettagli or ["gambe della stessa partita: non sono indipendenti"],
        })
    return avvisi


def prob_multipla_indipendente(probs_pct):
    """Prodotto delle probabilità (%), valido solo con gambe indipendenti."""
    p = 1.0
    for x in probs_pct:
        p *= x / 100
    return p * 100


def gambe_indipendenti(consigli, k):
    """Prime ``k`` giocate di ``consigli`` senza ripetere la stessa partita."""
    viste, scelte = set(), []
    for c in consigli:
        if c["partita"] in viste:
            continue
        viste.add(c["partita"])
        scelte.append(c)
        if len(scelte) == k:
            break
    return scelte


# ------------------------------------------------------------------
# Decadimento per data
# ------------------------------------------------------------------


def peso_per_eta(giorni, emivita):
    """Peso di una partita vecchia di ``giorni`` con emivita in giorni."""
    if emivita is None or emivita <= 0:
        return 1.0
    return 0.5 ** (max(giorni, 0) / emivita)
