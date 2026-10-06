"""Dal calendario alle previsioni da registrare (Poisson e Dixon–Coles).

Principio: UN solo calcolo dei gol attesi per partita (quello dell'app:
``modello.gol_attesi``) e DUE sole funzioni diverse per trasformarli in
probabilità. Così i due motori vedono gli stessi dati, lo stesso cutoff e le
stesse forze; l'unica differenza è il motore.

Configurazione congelata del test (modificarla = nuova serie, mai riscrittura):
  * forze: peso della forma d=0.95, prior=4, nessun decadimento per data;
  * tiri in porta: peso 0.3 quando entrambe le squadre hanno i dati (per
    partita si registra se sono stati usati);
  * assenze manuali: SPENTE (sono soggettive e dipendono dalla barra laterale);
  * calibrazione: NON applicata (si registrano le probabilità grezze);
  * Dixon–Coles con rho fisso (non quello eventualmente cambiato a mano).
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta

import motore_probabilistico
from config import TZ_ITALIA
from dati import normalizza_nome, trova_nome_fd
from modello import calcola_forze, esiti_poisson_puro, forze_tiri, gol_attesi

log = logging.getLogger("b-betting")

VERSIONE_APP = "b-betting 0.3.0"
RHO_REGISTRO = motore_probabilistico.RHO_DEFAULT
MARGINE_ORE_STESSO_GIORNO = 3  # incertezza sul fuso/orario della fonte

PARAMETRI_BASE = {
    "d": 0.95, "prior": 4, "emivita": None, "peso_tiri": 0.3,
    "assenze": False, "calibrazione": False, "max_gol": 8,
}
CONFIG_ID = hashlib.sha1(json.dumps(PARAMETRI_BASE, sort_keys=True).encode()).hexdigest()[:8]

MOTORI = ("poisson", "dixon_coles")
NOMI_MOTORE = {"poisson": "Poisson", "dixon_coles": "Dixon–Coles"}

MOTIVI = {
    "gia_giocata": "già giocata (ha un risultato)",
    "data_passata": "data già passata, senza risultato",
    "stesso_giorno": "gioca oggi: orario non verificabile come successivo alla registrazione",
    "squadra_senza_storico": "una squadra non ha storico nel modello",
    "storico_insufficiente": "meno di 10 partite giocate nel torneo: il modello non è stimabile",
}


def chiave_partita(camp, stagione, data, t1, t2):
    return f"{camp}|{stagione}|{str(data)[:10]}|{t1}|{t2}"


def _kickoff(m, tz=TZ_ITALIA):
    ora = str(m.get("time") or "").strip()[:5]
    try:
        return datetime.strptime(f"{str(m.get('date'))[:10]} {ora}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    except ValueError:
        return None


def _ha_risultato(m):
    sc = m.get("score")
    ft = sc.get("ft") if isinstance(sc, dict) else None
    return bool(ft) and len(ft) == 2


def perimetro(matches, da, a, adesso_dt):
    """Divide le partite della finestra [da, a] in (eleggibili, escluse).

    ``da`` e ``a`` sono date ISO 'YYYY-MM-DD'. Le partite fuori finestra non
    compaiono né tra le une né tra le altre. Ogni esclusa porta il motivo.
    Una partita di oggi è eleggibile solo con un orario noto e almeno
    ``MARGINE_ORE_STESSO_GIORNO`` ore nel futuro: la fonte può dare l'orario
    in un fuso diverso, e una previsione fatta dopo il fischio non vale.
    """
    oggi = adesso_dt.strftime("%Y-%m-%d")
    eleggibili, escluse = [], []
    for m in matches:
        if not isinstance(m, dict) or not m.get("team1") or not m.get("team2"):
            continue
        data = str(m.get("date", ""))[:10]
        if not (da <= data <= a):
            continue
        desc = f"{data} {m['team1']} - {m['team2']}"
        if _ha_risultato(m):
            escluse.append({"partita": m, "descrizione": desc, "motivo": "gia_giocata"})
        elif data < oggi:
            escluse.append({"partita": m, "descrizione": desc, "motivo": "data_passata"})
        elif data == oggi:
            ko = _kickoff(m)
            if ko is None or ko - adesso_dt < timedelta(hours=MARGINE_ORE_STESSO_GIORNO):
                escluse.append({"partita": m, "descrizione": desc, "motivo": "stesso_giorno"})
            else:
                eleggibili.append(m)
        else:
            eleggibili.append(m)
    eleggibili.sort(key=lambda m: (str(m.get("date")), str(m.get("time") or ""), m["team1"]))
    return eleggibili, escluse


def _storico(matches):
    gio = [m for m in matches if isinstance(m, dict) and _ha_risultato(m)]
    n_per_squadra = {}
    c1 = cx = c2 = co = cg = 0
    for m in gio:
        a, b = m["score"]["ft"]
        n_per_squadra[m["team1"]] = n_per_squadra.get(m["team1"], 0) + 1
        n_per_squadra[m["team2"]] = n_per_squadra.get(m["team2"], 0) + 1
        c1 += a > b; cx += a == b; c2 += a < b
        co += (a + b) > 2; cg += (a > 0 and b > 0)
    n = len(gio)
    base = None
    if n >= 10:
        base = {"b1": c1 / n, "bx": cx / n, "b2": c2 / n, "b_over25": co / n, "b_goal": cg / n}
    cutoff = max((str(m.get("date", ""))[:10] for m in gio), default=None)
    return n, n_per_squadra, base, cutoff


def calcola_batch(camp, stagione, matches, eleggibili, escluse, stato_dati="ok", df_stats=None):
    """Calcola le righe da registrare. Ritorna ``(record, esclusioni, cutoff, n_storico)``.

    Nessuna scrittura: serve anche per l'anteprima. Un errore su un motore non
    toglie la partita né l'altro motore: la riga porta ``errore`` e viene
    conservata come 'fallita'.
    """
    esclusioni = [
        {"match_key": chiave_partita(camp, stagione, e["partita"].get("date"), e["partita"]["team1"], e["partita"]["team2"]),
         "descrizione": e["descrizione"], "motivo": MOTIVI.get(e["motivo"], e["motivo"])}
        for e in escluse
    ]
    n, n_sq, base, cutoff = _storico(matches)
    modello = calcola_forze(matches, d=PARAMETRI_BASE["d"], prior=PARAMETRI_BASE["prior"])
    if not modello:
        for m in eleggibili:
            esclusioni.append({
                "match_key": chiave_partita(camp, stagione, m.get("date"), m["team1"], m["team2"]),
                "descrizione": f"{str(m.get('date'))[:10]} {m['team1']} - {m['team2']}",
                "motivo": MOTIVI["storico_insufficiente"],
            })
        return [], esclusioni, cutoff, n

    tiri = forze_tiri(df_stats)
    nomi = set()
    if tiri is not None and df_stats is not None:
        nomi = set(df_stats["HomeTeam"].dropna()) | set(df_stats["AwayTeam"].dropna())
    cache_nomi = {}

    def nome_fd(t):
        if t not in cache_nomi:
            cache_nomi[t] = trova_nome_fd(t, nomi) if nomi else None
        return cache_nomi[t]

    record = []
    for m in eleggibili:
        t1, t2 = m["team1"], m["team2"]
        data = str(m.get("date"))[:10]
        key = chiave_partita(camp, stagione, data, t1, t2)
        if t1 not in modello["forze"] or t2 not in modello["forze"]:
            mancante = t1 if t1 not in modello["forze"] else t2
            esclusioni.append({
                "match_key": key, "descrizione": f"{data} {t1} - {t2}",
                "motivo": f"{MOTIVI['squadra_senza_storico']} ({mancante})",
            })
            continue
        comune = {
            "match_key": key, "campionato": camp, "stagione": stagione, "data_partita": data,
            "ora_kickoff": str(m.get("time") or "") or None,
            "squadra_casa": t1, "squadra_ospite": t2, "config_id": CONFIG_ID,
            "n_storico": n, "n_storico_casa": n_sq.get(t1, 0), "n_storico_ospite": n_sq.get(t2, 0),
            "cutoff_dati": cutoff, "stato_dati": stato_dati,
            **(base or {}),
        }
        try:
            l1, l2, tiri_usati = gol_attesi(
                modello, t1, t2, tiri, nome_fd(t1), nome_fd(t2),
                peso_tiri=PARAMETRI_BASE["peso_tiri"], usa_assenze=False,
            )
        except Exception as e:  # noqa: BLE001 - la partita resta, segnata come fallita
            log.exception("Gol attesi non calcolabili: %s", key)
            for mot in MOTORI:
                record.append({**comune, "motore": mot, "versione_motore": f"{VERSIONE_APP}/{mot}",
                               "parametri": dict(PARAMETRI_BASE), "errore": f"gol attesi: {type(e).__name__}: {e}"})
            continue
        for mot in MOTORI:
            par = {**PARAMETRI_BASE, "motore": mot, "tiri_usati": bool(tiri_usati)}
            if mot == "dixon_coles":
                par["rho"] = RHO_REGISTRO
            rec = {**comune, "motore": mot, "versione_motore": f"{VERSIONE_APP}/{mot}", "parametri": par}
            try:
                if mot == "poisson":
                    e = esiti_poisson_puro(l1, l2, PARAMETRI_BASE["max_gol"])
                else:
                    e = motore_probabilistico.esiti_dixon_coles(
                        l1, l2, PARAMETRI_BASE["max_gol"], rho=RHO_REGISTRO)
                rec.update({
                    "l1": l1, "l2": l2,
                    "p1": e["1"] / 100, "px": e["X"] / 100, "p2": e["2"] / 100,
                    "p_over25": e["over25"] / 100, "p_goal": e["goal"] / 100,
                })
            except Exception as ex:  # noqa: BLE001
                log.exception("Motore %s fallito su %s", mot, key)
                rec["errore"] = f"{type(ex).__name__}: {ex}"
            record.append(rec)
    return record, esclusioni, cutoff, n


def controlla_nomi(squadre, df_stats):
    """Come i nomi delle squadre del calendario trovano il loro corrispondente nelle statistiche dei tiri.

    Ritorna una riga per squadra con ``tipo``: 'esatto' (stesso nome normalizzato),
    'approssimato' (trovato per prefisso o somiglianza: da controllare a occhio) oppure
    'assente' (nessun corrispondente: per quella squadra i tiri non si usano).
    Serve a vedere gli abbinamenti sbagliati PRIMA di registrare, non dopo.
    """
    if df_stats is None or len(df_stats) == 0 or "HomeTeam" not in df_stats.columns:
        return []
    nomi = set(df_stats["HomeTeam"].dropna()) | set(df_stats["AwayTeam"].dropna())
    righe = []
    for t in sorted(set(squadre)):
        trovato = trova_nome_fd(t, nomi)
        if trovato is None:
            tipo = "assente"
        elif normalizza_nome(t) == normalizza_nome(trovato):
            tipo = "esatto"
        else:
            tipo = "approssimato"
        righe.append({"squadra": t, "associato": trovato or "", "tipo": tipo})
    return righe
