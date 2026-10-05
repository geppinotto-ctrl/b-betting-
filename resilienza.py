"""Strumenti comuni per rendere la dashboard a prova di crash.

Contenuto:
  * ``http_get``            GET con retry/backoff e errori espliciti
  * ``ErroreDati``          eccezione per "dati non disponibili" (non va in cache)
  * ``valida_matches``      normalizza le partite una sola volta all'ingresso
  * ``sezione_sicura``      isola un blocco di UI: se fallisce, mostra un errore
                            e il resto della pagina continua a funzionare
  * ``registra_stato`` / ``mostra_stato_dati``
                            stato di caricamento dei dati, mostrato all'utente
  * ``svuota_cache``        pulizia SELETTIVA della cache (mai le quote API)

Nessuna dipendenza oltre a streamlit e requests.
"""

from __future__ import annotations

import contextlib
import logging
import time
import traceback

import requests
import streamlit as st

log = logging.getLogger("b-betting")

# Stati possibili di un caricamento dati
OK = "ok"
PARZIALE = "parziale"  # dati caricati ma alcune righe scartate
OBSOLETO = "obsoleto"  # download fallito, uso l'ultimo dato buono
VUOTO = "vuoto"  # la fonte risponde ma non ha dati (es. stagione futura)
ERRORE = "errore"  # download fallito e nessun dato precedente


class ErroreDati(RuntimeError):
    """Download o parsing fallito. Sollevata dalle funzioni in cache: Streamlit
    non memorizza le eccezioni, quindi un errore passeggero non resta in cache."""


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

_CODICI_RETRY = {429, 500, 502, 503, 504}


def http_get(url, *, params=None, headers=None, timeout=(4, 12), tentativi=3,
             pausa=0.6):
    """GET con retry e backoff esponenziale.

    Ritorna la ``Response`` per ogni codice NON ritentabile (200, 404, 401...):
    spetta al chiamante decidere. Solleva ``ErroreDati`` solo se, dopo tutti i
    tentativi, resta un errore di rete o un 429/5xx.
    """
    ultimo = "errore sconosciuto"
    for i in range(max(1, tentativi)):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code not in _CODICI_RETRY:
                return r
            ultimo = f"HTTP {r.status_code}"
        except requests.Timeout:
            ultimo = "timeout"
        except requests.ConnectionError:
            ultimo = "connessione non riuscita"
        except requests.RequestException as e:
            ultimo = f"{type(e).__name__}: {e}"
        log.warning("GET %s tentativo %d/%d fallito: %s", url, i + 1, tentativi, ultimo)
        if i < tentativi - 1:
            time.sleep(pausa * (2 ** i))
    raise ErroreDati(f"{ultimo} ({_host(url)})")


def _host(url):
    try:
        return url.split("/")[2]
    except Exception:
        return url


def json_sicuro(risposta):
    """Decodifica JSON; solleva ErroreDati (non ValueError) se non valido."""
    try:
        return risposta.json()
    except ValueError as e:
        raise ErroreDati("risposta non in formato JSON") from e


# --------------------------------------------------------------------------
# Validazione delle partite
# --------------------------------------------------------------------------

def _coppia_gol(v):
    """[a, b] di interi >= 0, altrimenti None."""
    if not isinstance(v, (list, tuple)) or len(v) != 2:
        return None
    try:
        a, b = float(v[0]), float(v[1])
    except (TypeError, ValueError):
        return None
    if a != a or b != b or a < 0 or b < 0 or a != int(a) or b != int(b):
        return None
    return [int(a), int(b)]


def valida_matches(matches):
    """Rende affidabile la lista partite per tutto il resto dell'app.

    Garanzie sull'output:
      * ogni elemento è un dict con ``team1`` e ``team2`` stringhe non vuote;
      * ``score`` è sempre un dict; ``score["ft"]`` e ``score["ht"]`` sono
        ``[int, int]`` oppure ``None`` (mai stringhe, mai liste corte).

    Ritorna ``(partite_valide, n_scartate, n_punteggi_corretti)``.
    """
    valide, scartate, corretti = [], 0, 0
    for m in matches if isinstance(matches, list) else []:
        if not isinstance(m, dict):
            scartate += 1
            continue
        t1, t2 = m.get("team1"), m.get("team2")
        if not isinstance(t1, str) or not isinstance(t2, str) or not t1.strip() or not t2.strip():
            scartate += 1
            continue
        nuovo = dict(m)
        sc = m.get("score")
        sc = sc if isinstance(sc, dict) else {}
        ft, ht = _coppia_gol(sc.get("ft")), _coppia_gol(sc.get("ht"))
        if (sc.get("ft") is not None and ft is None) or (sc.get("ht") is not None and ht is None):
            corretti += 1
        # un primo tempo con più gol del finale è un dato incoerente
        if ft and ht and (ht[0] > ft[0] or ht[1] > ft[1]):
            ht = None
            corretti += 1
        nuovo["score"] = {"ft": ft, "ht": ht}
        valide.append(nuovo)
    return valide, scartate, corretti


def abbastanza_partite(matches, minimo=10):
    """True se ci sono almeno ``minimo`` partite con risultato finale."""
    n = sum(1 for m in matches or [] if isinstance(m, dict)
            and isinstance(m.get("score"), dict) and m["score"].get("ft"))
    return n >= minimo


# --------------------------------------------------------------------------
# Stato dei caricamenti (mostrato all'utente)
# --------------------------------------------------------------------------

def registra_stato(chiave, stato, messaggio="", quando=None):
    """Annota l'esito di un caricamento. Sicuro anche fuori da una sessione."""
    try:
        reg = st.session_state.setdefault("_stato_dati", {})
        reg[chiave] = {"stato": stato, "messaggio": messaggio, "quando": quando}
    except Exception:
        pass


def mostra_stato_dati(chiavi=None, dove=None):
    """Mostra avvisi per i caricamenti non perfetti. Ritorna True se tutto ok."""
    dove = dove or st
    try:
        reg = st.session_state.get("_stato_dati", {})
    except Exception:
        return True
    tutto_ok = True
    for k, v in reg.items():
        if chiavi is not None and k not in chiavi:
            continue
        s, msg = v["stato"], v["messaggio"]
        if s == ERRORE:
            dove.error(f"❌ {msg}")
            tutto_ok = False
        elif s in (OBSOLETO, VUOTO, PARZIALE):
            dove.warning(f"⚠️ {msg}")
            tutto_ok = False
    return tutto_ok


# --------------------------------------------------------------------------
# Isolamento delle sezioni di UI
# --------------------------------------------------------------------------

@contextlib.contextmanager
def sezione_sicura(nome, contenitore=None):
    """Esegue un blocco di UI senza mai far cadere la pagina.

        with sezione_sicura("Backtest", tab5):
            mostra_backtest(matches, tab5)

    Se il blocco solleva un'eccezione viene mostrato un ``st.error`` con il nome
    della sezione e i dettagli tecnici in un expander. Le eccezioni di controllo
    di Streamlit (``st.stop``, ``st.rerun``) NON vengono intercettate.
    """
    ctx = contenitore if contenitore is not None else contextlib.nullcontext()
    with ctx:
        try:
            yield
        except Exception as e:  # noqa: BLE001
            if _e_controllo_streamlit(e):
                raise
            log.exception("Errore nella sezione %s", nome)
            st.error(
                f"❌ La sezione «{nome}» non è disponibile: {type(e).__name__}. "
                "Le altre sezioni funzionano normalmente. Riprova con "
                "«Aggiorna Dati»."
            )
            with st.expander("Dettagli tecnici"):
                st.code(traceback.format_exc())


def _e_controllo_streamlit(e):
    """st.stop / st.rerun sono eccezioni: vanno lasciate passare."""
    nome = type(e).__name__
    return nome in ("StopException", "RerunException", "ScriptControlException")


# --------------------------------------------------------------------------
# Calcoli lunghi con barra di progresso
# --------------------------------------------------------------------------

def calcolo_con_progresso(chiave, funzione, testo="Calcolo in corso", ttl=3600,
                          salva=True):
    """Esegue ``funzione(avanzamento)`` mostrando una barra di progresso reale.

    ``avanzamento(frazione, dettaglio="")`` accetta valori da 0 a 1. Il risultato
    resta in ``session_state`` per ``ttl`` secondi (come farebbe st.cache_data,
    che però non permette di aggiornare una barra dall'interno). Con
    ``salva=False`` (dati incompleti) il risultato non viene conservato.
    Le eccezioni della funzione salgono al chiamante.
    """
    memo = st.session_state.setdefault("_calcoli", {})
    voce = memo.get(chiave)
    if voce and time.time() - voce[0] < ttl:
        return voce[1]

    barra = st.progress(0.0, text=f"{testo}…")

    def avanzamento(frazione, dettaglio=""):
        try:
            f = min(max(float(frazione), 0.0), 1.0)
            barra.progress(f, text=f"{testo}… {int(f * 100)}% {dettaglio}".strip())
        except Exception:  # la barra è un di più: non deve mai rompere il calcolo
            pass

    try:
        risultato = funzione(avanzamento)
    finally:
        barra.empty()
    if salva:
        memo[chiave] = (time.time(), risultato)
    return risultato


def stagioni_con_problemi(campionato, stagioni, carica):
    """Stagioni il cui caricamento è fallito o obsoleto (``carica`` = loader)."""
    guaste = []
    for stag in stagioni:
        try:
            if carica(campionato, stag).get("stato") in (ERRORE, OBSOLETO):
                guaste.append(stag)
        except Exception:  # noqa: BLE001
            guaste.append(stag)
    return guaste


# --------------------------------------------------------------------------
# Cache selettiva
# --------------------------------------------------------------------------

# (modulo, funzione) raggruppati per ciò che dipende da cosa.
_GRUPPI = {
    # file scaricati da internet
    "download": [
        ("dati", "_campionato_cached"),
        ("dati", "_stats_cached"),
    ],
    # calcoli pesanti: dipendono da dati, motore, rho e assenze
    "calcoli": [
        ("modello", "esegui_backtest"),
        ("modello", "_consigli_cached"),
        ("confronto_mercato", "_confronto_cached"),
        ("assenze", "_carica_cached"),
    ],
}


def svuota_cache(*gruppi):
    """Svuota solo i gruppi indicati ("download", "calcoli").

    Le quote API (``quote.py``) non vengono mai toccate: ogni richiesta consuma
    crediti del provider. Per cancellare anche quelle usare ``svuota_quote``.
    """
    import importlib

    for g in gruppi:
        for mod, nome in _GRUPPI.get(g, []):
            try:
                f = getattr(importlib.import_module(mod), nome, None)
                if f is not None and hasattr(f, "clear"):
                    f.clear()
            except Exception:  # noqa: BLE001 - la pulizia non deve mai rompere l'app
                log.exception("Pulizia cache fallita per %s.%s", mod, nome)
    try:
        st.session_state.pop("_stato_dati", None)
        if "calcoli" in gruppi:
            st.session_state.pop("_calcoli", None)
    except Exception:
        pass


def svuota_quote():
    """Svuota la cache delle quote (consuma richieste API alla prossima visita)."""
    import importlib

    for nome in ("_quote_lista_cached", "_mercati_cached", "_testa_cached"):
        try:
            f = getattr(importlib.import_module("quote"), nome, None)
            if f is not None and hasattr(f, "clear"):
                f.clear()
        except Exception:  # noqa: BLE001
            log.exception("Pulizia cache quote fallita: %s", nome)
    try:
        st.session_state.pop("_quote_fail", None)
        st.session_state.pop("_mercati_fail", None)
    except Exception:
        pass
