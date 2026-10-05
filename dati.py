"""Caricamento dati (partite e statistiche extra).

Regole di resilienza:
  * le funzioni ``_..._cached`` SOLLEVANO ``ErroreDati`` se il download fallisce:
    Streamlit non mette in cache le eccezioni, quindi un timeout passeggero non
    "avvelena" la cache per 30 minuti come faceva il vecchio ``{"matches": []}``;
  * le funzioni pubbliche NON sollevano mai: ripiegano sull'ultimo dato buono
    (stato "obsoleto") oppure su un risultato vuoto (stato "errore") e annotano
    l'esito con ``registra_stato`` perché la UI possa avvisare l'utente;
  * le partite passano da ``valida_matches``: il resto dell'app può fidarsi
    che ``score["ft"]`` sia ``[int, int]`` oppure ``None``.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import difflib
import io
import logging
import re

import pandas as pd
import streamlit as st

from config import TZ_ITALIA, mapping_file_torneo
from resilienza import (
    ERRORE, OBSOLETO, OK, PARZIALE, VUOTO, ErroreDati,
    http_get, json_sicuro, registra_stato, valida_matches,
)

log = logging.getLogger("b-betting")

ESPN_CL_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/scoreboard"
)
RAW_URL = "https://raw.githubusercontent.com/openfootball/football.json/master/"

# Ultimo dato buono per (campionato, stagione): serve da ripiego se un
# aggiornamento successivo fallisce. Vive finché vive il processo.
_ULTIMO_BUONO = {}
_ULTIME_STATS = {}


def chiave_stato(nome_campionato, stagione):
    return f"matches:{nome_campionato}:{stagione}"


def _converti_evento_cl(evento):
    comp = (evento.get("competitions") or [{}])[0]
    competitors = comp.get("competitors", [])
    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
    if not home or not away:
        return None
    nome1 = (home.get("team") or {}).get("displayName")
    nome2 = (away.get("team") or {}).get("displayName")
    if not nome1 or not nome2:
        return None

    iso = str(evento.get("date", ""))
    data, ora = iso[:10], ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ_ITALIA)
        data, ora = dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    except Exception:
        pass

    stato = ((evento.get("status") or comp.get("status") or {}).get("type")) or {}
    finita = stato.get("completed") is True or stato.get("state") == "post"

    ft = ht = None
    if finita:
        try:
            ft = [int(float(home.get("score"))), int(float(away.get("score")))]
        except Exception:
            ft = None
        try:
            lh = home.get("linescores") or []
            la = away.get("linescores") or []
            if len(lh) >= 2 and len(la) >= 2:
                ht = [int(float(lh[0].get("value"))), int(float(la[0].get("value")))]
        except Exception:
            ht = None

    return {
        "id": evento.get("id"),
        "date": data,
        "time": ora,
        "team1": nome1,
        "team2": nome2,
        "score": {"ft": ft, "ht": ht},
    }


def _scarica_anno_cl(anno):
    """ESPN accetta dates=ANNO (gli intervalli danno HTTP 400)."""
    ultimo = "nessuna risposta"
    for params in ({"dates": str(anno), "limit": 1000}, {"dates": str(anno)}):
        r = http_get(ESPN_CL_URL, params=params, timeout=(4, 15), tentativi=2)
        if r.status_code == 200:
            dati = json_sicuro(r)
            eventi = dati.get("events") if isinstance(dati, dict) else None
            return eventi if isinstance(eventi, list) else []
        ultimo = f"HTTP {r.status_code}"
    raise ErroreDati(f"ESPN {ultimo} per l'anno {anno}")


def _scarica_champions(stagione):
    anno = int(stagione.split("-")[0])
    inizio, fine = f"{anno}-09-01", f"{anno + 1}-06-30"  # esclude i preliminari
    visti, matches = set(), []
    with ThreadPoolExecutor(max_workers=2) as ex:
        # Le due annate servono entrambe: se una fallisce, l'eccezione sale e
        # il risultato incompleto NON viene messo in cache.
        for eventi in ex.map(_scarica_anno_cl, [anno, anno + 1]):
            for ev in eventi:
                try:
                    m = _converti_evento_cl(ev)
                except Exception:  # un evento malformato non blocca gli altri
                    log.exception("Evento Champions non convertibile")
                    continue
                if not m or m["id"] in visti:
                    continue
                if not (inizio <= m["date"] <= fine):
                    continue
                visti.add(m["id"])
                matches.append(m)
    matches.sort(key=lambda m: (m["date"], m["time"]))
    return matches


def _stagione_coerente(matches, stagione):
    """True se le date delle partite cadono nella stagione richiesta.

    Il download prova anche percorsi senza stagione: senza questo controllo si
    potrebbero mostrare, senza dirlo, i dati di un'altra annata.
    """
    try:
        anno = int(stagione.split("-")[0])
    except Exception:
        return True
    anni = [str(m.get("date", ""))[:4] for m in matches if isinstance(m, dict)]
    anni = [a for a in anni if a.isdigit()]
    if not anni:
        return True
    ok = sum(1 for a in anni if int(a) in (anno, anno + 1))
    return ok / len(anni) >= 0.8


def _estrai_matches(res):
    if isinstance(res, list):
        return res
    if isinstance(res, dict):
        if isinstance(res.get("matches"), list):
            return res["matches"]
        for v in res.values():
            if isinstance(v, list):
                return v
    return []


def _scarica_openfootball(nome_campionato, stagione):
    possibili_nomi = mapping_file_torneo.get(nome_campionato, ["it.1.json"])
    anno_inizio = stagione.split("-")[0]
    percorsi = []
    for nome_file in possibili_nomi:
        percorsi += [f"{stagione}/{nome_file}", nome_file, f"{anno_inizio}/{nome_file}"]

    errori_rete = 0
    ultimo_errore = ""
    for p in percorsi:
        try:
            r = http_get(RAW_URL + p, timeout=(4, 10), tentativi=2)
        except ErroreDati as e:
            errori_rete += 1
            ultimo_errore = str(e)
            if errori_rete >= 2:  # rete giù: inutile provare gli altri percorsi
                raise ErroreDati(f"Download fallito: {ultimo_errore}") from e
            continue
        if r.status_code != 200:
            continue  # 404 = quel percorso non esiste, si prova il successivo
        try:
            matches = _estrai_matches(json_sicuro(r))
        except ErroreDati:
            continue
        if matches and _stagione_coerente(matches, stagione):
            return matches
    if errori_rete:
        raise ErroreDati(f"Download fallito: {ultimo_errore}")
    return []  # la fonte risponde ma non ha questa stagione: vuoto legittimo


@st.cache_data(ttl=1800, show_spinner=False)
def _campionato_cached(nome_campionato, stagione):
    """Scarica e valida. Solleva ErroreDati se il download fallisce."""
    if nome_campionato == "UEFA Champions League":
        grezze = _scarica_champions(stagione)
    else:
        grezze = _scarica_openfootball(nome_campionato, stagione)
    matches, scartate, corretti = valida_matches(grezze)
    return {
        "matches": matches,
        "scartate": scartate,
        "corretti": corretti,
        "scaricato_alle": datetime.now(TZ_ITALIA).strftime("%d/%m %H:%M"),
    }


def carica_dati_campionato(nome_campionato, stagione):
    """Partite di un torneo. Non solleva MAI.

    Ritorna un dict con ``matches`` (sempre una lista) più ``stato``
    (ok/parziale/obsoleto/vuoto/errore), ``messaggio`` e ``scaricato_alle``.
    """
    k = chiave_stato(nome_campionato, stagione)
    try:
        dati = _campionato_cached(nome_campionato, stagione)
    except Exception as e:  # noqa: BLE001 - qualsiasi errore deve degradare
        log.warning("Caricamento %s %s fallito: %s", nome_campionato, stagione, e)
        vecchio = _ULTIMO_BUONO.get((nome_campionato, stagione))
        if vecchio and vecchio["matches"]:
            msg = (f"{nome_campionato} {stagione}: aggiornamento non riuscito ({e}). "
                   f"Mostro gli ultimi dati validi, del {vecchio['scaricato_alle']}.")
            registra_stato(k, OBSOLETO, msg)
            return {**vecchio, "stato": OBSOLETO, "messaggio": msg}
        msg = (f"{nome_campionato} {stagione}: impossibile scaricare i dati ({e}). "
               "Controlla la connessione e premi «Aggiorna Dati».")
        registra_stato(k, ERRORE, msg)
        return {"matches": [], "scartate": 0, "corretti": 0,
                "scaricato_alle": "", "stato": ERRORE, "messaggio": msg}

    if not dati["matches"]:
        msg = (f"{nome_campionato} {stagione}: nessuna partita disponibile "
               "(la stagione potrebbe non essere ancora iniziata o pubblicata).")
        registra_stato(k, VUOTO, msg)
        return {**dati, "stato": VUOTO, "messaggio": msg}

    _ULTIMO_BUONO[(nome_campionato, stagione)] = dati
    if dati["scartate"] or dati["corretti"]:
        msg = (f"{nome_campionato} {stagione}: {dati['scartate']} partite scartate e "
               f"{dati['corretti']} risultati corretti perché incompleti o incoerenti.")
        registra_stato(k, PARZIALE, msg)
        return {**dati, "stato": PARZIALE, "messaggio": msg}
    registra_stato(k, OK, "")
    return {**dati, "stato": OK, "messaggio": ""}


def carica_dati_champions(stagione):
    return carica_dati_campionato("UEFA Champions League", stagione)


CODICI_FD = {
    "Italia - Serie A": "I1",
    "Inghilterra - Premier League": "E0",
    "Spagna - La Liga": "SP1",
    "Germania - Bundesliga": "D1",
    "Francia - Ligue 1": "F1",
}


@st.cache_data(ttl=3600, show_spinner=False)
def _stats_cached(campionato, stagione):
    """CSV football-data.co.uk. None = non esiste per questa stagione (legittimo,
    si può mettere in cache); ErroreDati = problema di rete (non in cache)."""
    codice = CODICI_FD.get(campionato)
    if not codice:
        return None
    try:
        anno_a = stagione.split("-")[0][2:]
        anno_b = stagione.split("-")[1]
    except IndexError:
        return None
    url = f"https://www.football-data.co.uk/mmz4281/{anno_a}{anno_b}/{codice}.csv"
    r = http_get(url, timeout=(4, 12), tentativi=2)
    if r.status_code != 200:
        return None
    try:
        df = pd.read_csv(io.BytesIO(r.content), encoding="latin-1", on_bad_lines="skip")
    except Exception as e:  # CSV illeggibile: non è un errore di rete, ma nemmeno un dato
        log.warning("CSV %s non leggibile: %s", url, e)
        return None
    if "HomeTeam" not in df.columns or "AwayTeam" not in df.columns:
        return None
    df = df.dropna(subset=["HomeTeam", "AwayTeam"])
    return df if not df.empty else None


def carica_stats_extra(campionato, stagione):
    """DataFrame con angoli/tiri/cartellini, oppure None. Non solleva MAI.

    Se l'aggiornamento fallisce ripiega sull'ultimo DataFrame valido."""
    try:
        df = _stats_cached(campionato, stagione)
    except Exception as e:  # noqa: BLE001
        log.warning("Stats extra %s %s non scaricabili: %s", campionato, stagione, e)
        vecchio = _ULTIME_STATS.get((campionato, stagione))
        registra_stato(
            f"stats:{campionato}:{stagione}", OBSOLETO,  # degradato, non fatale
            f"Statistiche extra (tiri, angoli) di {campionato} non aggiornate ({e}). "
            + ("Uso gli ultimi dati validi." if vecchio is not None
               else "Le analisi che le usano vengono saltate."),
        )
        return vecchio
    if df is not None:
        _ULTIME_STATS[(campionato, stagione)] = df
    return df


def normalizza_nome(nome):
    n = re.sub(r"[^a-z ]", " ", str(nome).lower())
    togli = {"fc", "ac", "as", "ss", "ssc", "us", "acf", "afc", "cfc", "bc",
             "calcio", "hellas", "club", "de", "di"}
    return " ".join(p for p in n.split() if p not in togli)


def trova_nome_fd(nome, nomi_fd):
    n = normalizza_nome(nome)
    if not n:
        return None
    mappa = {normalizza_nome(x): x for x in nomi_fd}
    if n in mappa:
        return mappa[n]
    for k, v in mappa.items():
        if k and (n.startswith(k) or k.startswith(n)):
            return v
    simili = difflib.get_close_matches(n, list(mappa.keys()), n=1, cutoff=0.8)
    return mappa[simili[0]] if simili else None


def calcola_stats_extra(df, nome):
    nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
    nome_fd = trova_nome_fd(nome, nomi)
    if not nome_fd:
        return None
    casa = df[df["HomeTeam"] == nome_fd]
    fuori = df[df["AwayTeam"] == nome_fd]
    tot = len(casa) + len(fuori)
    if tot == 0:
        return None

    def media(col_casa, col_fuori):
        if col_casa not in df.columns or col_fuori not in df.columns:
            return None
        v = (
            pd.to_numeric(casa[col_casa], errors="coerce").dropna().tolist()
            + pd.to_numeric(fuori[col_fuori], errors="coerce").dropna().tolist()
        )
        return round(sum(v) / len(v), 2) if v else None

    return {
        "nome_fd": nome_fd,
        "tot": tot,
        "angoli_f": media("HC", "AC"),
        "angoli_s": media("AC", "HC"),
        "tiri_f": media("HS", "AS"),
        "tiri_s": media("AS", "HS"),
        "porta_f": media("HST", "AST"),
        "porta_s": media("AST", "HST"),
        "falli": media("HF", "AF"),
        "gialli": media("HY", "AY"),
        "rossi": media("HR", "AR"),
    }
