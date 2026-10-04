"""Motore probabilistico Dixon–Coles + simulatore di stagione Monte Carlo.

Sostituisce `esiti_poisson`, `matrice_risultati` e `distribuzione_gol_totali`
di modello.py con lo stesso formato di output.

Differenze rispetto alla bozza di Copilot:
  * la correzione tau è quella del paper originale (dipende da λ e μ),
  * la matrice è rinormalizzata (somma = 1),
  * con rho = 0 il risultato coincide ESATTAMENTE con il Poisson attuale,
  * le probabilità sono calcolate in forma esatta (niente rumore Monte Carlo),
  * il Monte Carlo è usato solo dove serve: la simulazione della stagione,
    che parte dalla classifica reale e simula solo le partite rimaste.

Dipende solo da numpy.
"""

import math

import numpy as np

# ρ tipico per il calcio europeo nella parametrizzazione del paper originale
# (valori negativi => più 0-0 e 1-1 del Poisson). Va stimato dai dati con
# `stima_rho`: questo è solo il valore di partenza.
RHO_DEFAULT = -0.10

MAX_GOL = 8

_LOG_FATT = [math.lgamma(i + 1) for i in range(60)]


# --------------------------------------------------------------------------
# Nucleo: matrice dei risultati
# --------------------------------------------------------------------------

def _pmf(lam, n):
    """Probabilità Poisson di 0..n gol."""
    lam = max(float(lam), 1e-9)
    k = np.arange(n + 1)
    lf = np.array(_LOG_FATT[: n + 1])
    return np.exp(-lam + k * math.log(lam) - lf)


def rho_valido(l1, l2, rho):
    """Limita rho all'intervallo in cui tutti i fattori tau restano positivi."""
    l1 = max(float(l1), 1e-9)
    l2 = max(float(l2), 1e-9)
    basso = max(-1.0 / l1, -1.0 / l2)
    alto = min(1.0 / (l1 * l2), 1.0)
    # margine per non arrivare a tau = 0
    return min(max(rho, basso * 0.99), alto * 0.99)


def matrice_dc(l1, l2, rho=RHO_DEFAULT, max_gol=MAX_GOL):
    """Matrice (max_gol+1)x(max_gol+1) di probabilità (somma 1).

    m[i, j] = P(casa segna i, ospite segna j) con la correzione di
    Dixon–Coles (1997) sui punteggi 0-0, 0-1, 1-0, 1-1.
    """
    n = max(int(max_gol), 1)
    m = np.outer(_pmf(l1, n), _pmf(l2, n))
    r = rho_valido(l1, l2, rho)
    l1c = max(float(l1), 1e-9)
    l2c = max(float(l2), 1e-9)
    m[0, 0] *= 1.0 - l1c * l2c * r
    m[0, 1] *= 1.0 + l1c * r
    m[1, 0] *= 1.0 + l2c * r
    m[1, 1] *= 1.0 - r
    return m / m.sum()


def _riassumi(m):
    """Mercati principali (in %) da una matrice di probabilità."""
    n = m.shape[0]
    i, j = np.indices(m.shape)
    p1 = float(m[i > j].sum())
    px = float(m[i == j].sum())
    p2 = float(m[i < j].sum())
    over25 = float(m[(i + j) > 2].sum())
    btts = float(m[(i > 0) & (j > 0)].sum())
    return p1, px, p2, over25, btts


def esiti_dixon_coles(l1, l2, max_gol=MAX_GOL, rho=RHO_DEFAULT):
    """Stesso formato di `modello.esiti_poisson`."""
    m = matrice_dc(l1, l2, rho, max_gol)
    p1, px, p2, over25, btts = _riassumi(m)
    n = m.shape[0]
    risultati = [(f"{a}-{b}", float(m[a, b])) for a in range(n) for b in range(n)]
    risultati.sort(key=lambda x: x[1], reverse=True)
    return {
        "1": p1 * 100,
        "X": px * 100,
        "2": p2 * 100,
        "over25": over25 * 100,
        "under25": (1 - over25) * 100,
        "goal": btts * 100,
        "nogoal": (1 - btts) * 100,
        "top": risultati[:5],
    }


def matrice_risultati_dc(l1, l2, max_gol=5, rho=RHO_DEFAULT):
    """Come `modello.matrice_risultati`: lista di liste in %, 0..max_gol."""
    m = matrice_dc(l1, l2, rho, MAX_GOL) * 100
    return [[float(m[i, j]) for j in range(max_gol + 1)] for i in range(max_gol + 1)]


def distribuzione_gol_totali_dc(l1, l2, max_mostrati=7, rho=RHO_DEFAULT):
    """Come `modello.distribuzione_gol_totali`: % di 0,1,...,max-1 e 'max o più'."""
    m = matrice_dc(l1, l2, rho, MAX_GOL) * 100
    n = m.shape[0]
    dist = [0.0] * (2 * n - 1)
    for i in range(n):
        for j in range(n):
            dist[i + j] += float(m[i, j])
    return dist[:max_mostrati] + [sum(dist[max_mostrati:])]


# --------------------------------------------------------------------------
# Stima di rho dai dati
# --------------------------------------------------------------------------

def stima_rho(partite, modello, griglia=None, max_gol=MAX_GOL):
    """Stima rho per massima verosimiglianza su partite già giocate.

    partite: lista di (squadra_casa, squadra_ospite, gol_casa, gol_ospite)
    modello: dizionario di `modello.calcola_forze` ({'mc','mf','forze'})
    Restituisce (rho_migliore, tabella[(rho, loglik)]).

    I λ vengono calcolati con le forze su tutto il campione (in-sample): va
    bene per UN solo parametro, ma il valore va comunque verificato con
    `confronta_motori.py`, che valuta fuori campione.
    """
    if griglia is None:
        griglia = [round(x, 3) for x in np.arange(-0.30, 0.1001, 0.01)]
    forze = modello["forze"]
    dati = []
    for t1, t2, a, b in partite:
        if t1 in forze and t2 in forze and a <= max_gol and b <= max_gol:
            l1 = modello["mc"] * forze[t1]["att"] * forze[t2]["dif"]
            l2 = modello["mf"] * forze[t2]["att"] * forze[t1]["dif"]
            dati.append((l1, l2, int(a), int(b)))
    if len(dati) < 30:
        return RHO_DEFAULT, []
    tabella = []
    for rho in griglia:
        ll = 0.0
        for l1, l2, a, b in dati:
            p = matrice_dc(l1, l2, rho, max_gol)[a, b]
            ll += math.log(max(p, 1e-12))
        tabella.append((rho, ll))
    migliore = max(tabella, key=lambda x: x[1])[0]
    return migliore, tabella


# --------------------------------------------------------------------------
# Simulatore di stagione
# --------------------------------------------------------------------------

def _lambda_modello(modello, t1, t2):
    f = modello["forze"]
    return (
        modello["mc"] * f[t1]["att"] * f[t2]["dif"],
        modello["mf"] * f[t2]["att"] * f[t1]["dif"],
    )


def simula_stagione(
    matches,
    modello,
    rho=RHO_DEFAULT,
    n_sim=5000,
    seed=None,
    lambda_fn=None,
    n_champions=4,
    n_retrocesse=3,
    max_gol=MAX_GOL,
):
    """Simula le partite rimaste e ricava la classifica finale attesa.

    matches:  lista nel formato openfootball (team1, team2, score.ft se giocata)
    modello:  output di `calcola_forze`
    lambda_fn(t1, t2) -> (l1, l2) per usare gol attesi personalizzati
              (tiri, assenze...). Di default usa solo le forze del modello.

    Le partite già giocate entrano con il risultato reale; si simulano solo
    quelle senza risultato. Restituisce una lista ordinata per punti attesi.
    """
    if not modello:
        return []
    forze = modello["forze"]
    if lambda_fn is None:
        def lambda_fn(a, b):
            return _lambda_modello(modello, a, b)

    squadre = sorted(forze.keys())
    idx = {s: i for i, s in enumerate(squadre)}
    n_sq = len(squadre)

    pt0 = np.zeros(n_sq)
    gf0 = np.zeros(n_sq)
    gs0 = np.zeros(n_sq)
    pg0 = np.zeros(n_sq)
    da_giocare = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        t1, t2 = m.get("team1"), m.get("team2")
        if t1 not in idx or t2 not in idx:
            continue
        s = m.get("score")
        ft = s.get("ft") if isinstance(s, dict) else None
        if ft:
            a, b = ft[0], ft[1]
            i, j = idx[t1], idx[t2]
            gf0[i] += a
            gs0[i] += b
            gf0[j] += b
            gs0[j] += a
            pg0[i] += 1
            pg0[j] += 1
            if a > b:
                pt0[i] += 3
            elif a == b:
                pt0[i] += 1
                pt0[j] += 1
            else:
                pt0[j] += 3
        else:
            da_giocare.append((idx[t1], idx[t2], t1, t2))

    rng = np.random.default_rng(seed)
    pts = np.tile(pt0, (n_sim, 1))
    gf = np.tile(gf0, (n_sim, 1))
    gs = np.tile(gs0, (n_sim, 1))

    n1 = max_gol + 1
    for i, j, t1, t2 in da_giocare:
        l1, l2 = lambda_fn(t1, t2)
        cdf = np.cumsum(matrice_dc(l1, l2, rho, max_gol).ravel())
        cdf[-1] = 1.0
        k = np.searchsorted(cdf, rng.random(n_sim), side="right")
        k = np.minimum(k, n1 * n1 - 1)
        a = k // n1
        b = k % n1
        gf[:, i] += a
        gs[:, i] += b
        gf[:, j] += b
        gs[:, j] += a
        pts[:, i] += np.where(a > b, 3, np.where(a == b, 1, 0))
        pts[:, j] += np.where(b > a, 3, np.where(a == b, 1, 0))

    # classifica: punti, differenza reti, gol fatti; sorteggio sugli ex aequo
    chiave = (
        pts * 1e6
        + (gf - gs + 500) * 1e3
        + gf
        + rng.random(pts.shape) * 0.1
    )
    ordine = np.argsort(-chiave, axis=1)
    posizione = np.empty_like(ordine)
    righe = np.arange(n_sim)[:, None]
    posizione[righe, ordine] = np.arange(1, n_sq + 1)[None, :]

    risultati = []
    for s, i in idx.items():
        conteggi = np.bincount(posizione[:, i], minlength=n_sq + 1)[1:]
        pos_pct = {p + 1: float(conteggi[p]) / n_sim * 100 for p in range(n_sq)}
        risultati.append(
            {
                "squadra": s,
                "punti_attuali": int(pt0[i]),
                "partite_giocate": int(pg0[i]),
                "media_punti": float(pts[:, i].mean()),
                "posizioni": {p: v for p, v in pos_pct.items() if v > 0},
                "p_titolo": pos_pct[1],
                "p_champions": sum(pos_pct[p] for p in range(1, min(n_champions, n_sq) + 1)),
                "p_retrocessione": sum(
                    pos_pct[p] for p in range(max(n_sq - n_retrocesse + 1, 1), n_sq + 1)
                ),
            }
        )
    risultati.sort(key=lambda r: r["media_punti"], reverse=True)
    return risultati
