"""Backup remoto opzionale su un repository GitHub PRIVATO.

Perché: su Streamlit Community Cloud il disco si azzera quando l'app si riavvia o va
in pausa. Senza una copia fuori dal disco, archivio previsioni, schedine e curve
sparirebbero. Qui la copia sta in un repository privato scelto dall'utente.

Si attiva SOLO se nei «Secrets» dell'app ci sono:
    GITHUB_BACKUP_TOKEN = "github_pat_..."        (permesso: Contents, lettura e scrittura, su quel solo repo)
    GITHUB_BACKUP_REPO  = "utente/nome-repo-privato"
    GITHUB_BACKUP_BRANCH = "main"                 (facoltativo)
Senza questi valori non succede nulla e resta il backup manuale.

Regole di sicurezza dei dati:
  * mai sovrascrivere alla cieca: prima di caricare l'archivio previsioni si SCARICA
    la copia remota e la si UNISCE a quella locale (un'unione non cancella niente);
    se il download fallisce, non si carica;
  * stato.json e registro CSV si caricano solo dopo che il ripristino di quel file è
    andato a buon fine in questa sessione (altrimenti un riavvio seguito da un salvataggio
    cancellerebbe lo storico remoto);
  * nessuna funzione pubblica solleva eccezioni; il token non compare mai in messaggi o log;
  * i file sono pochi e piccoli (centinaia di KB).
"""

import base64
import hashlib
import logging
import os
import time
from pathlib import Path

import persistenza
import previsioni_db as DB

log = logging.getLogger("b-betting")

CARTELLA_REMOTA = "b-betting"
TIMEOUT = (5, 20)
PAUSA_FILE_LEGGERI = 120  # secondi tra due caricamenti di stato.json / registro CSV

NOMI = ("previsioni.db", "stato.json", "registro_pronostici.csv")


# ------------------------------------------------------------------
# Configurazione e file locali
# ------------------------------------------------------------------


def configurazione():
    """Dizionario con token, repo, branch oppure None se non configurato."""
    def leggi(chiave):
        v = os.environ.get(chiave, "")
        if not v:
            try:
                import streamlit as st

                v = st.secrets.get(chiave, "") or ""
            except Exception:  # noqa: BLE001 - nessun file secrets: normale
                v = ""
        return str(v).strip()

    token, repo = leggi("GITHUB_BACKUP_TOKEN"), leggi("GITHUB_BACKUP_REPO")
    if not token or "/" not in repo:
        return None
    return {"token": token, "repo": repo, "branch": leggi("GITHUB_BACKUP_BRANCH") or "main"}


def percorso_locale(nome):
    if nome == "previsioni.db":
        return DB.percorso_db(prova=False)
    if nome == "stato.json":
        return persistenza.percorso()
    if nome == "registro_pronostici.csv":
        import registro

        return Path(registro.FILE_REGISTRO)
    raise ValueError(nome)


def _stato_sessione():
    try:
        import streamlit as st

        return st.session_state
    except Exception:  # noqa: BLE001
        return {}


# ------------------------------------------------------------------
# API GitHub (contents)
# ------------------------------------------------------------------


class ErroreRemoto(Exception):
    """Errore di rete o di GitHub, con un messaggio leggibile e senza segreti."""


def _intestazioni(cfg, raw=False):
    return {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "b-betting-backup",
    }


def _url(cfg, nome):
    return f"https://api.github.com/repos/{cfg['repo']}/contents/{CARTELLA_REMOTA}/{nome}"


def _spiega(r):
    if r.status_code in (401, 403):
        return "token non valido, scaduto o senza permesso di scrittura sul repository"
    if r.status_code == 404:
        return "repository non trovato (controlla nome e permessi del token)"
    if r.status_code == 409:
        return "conflitto di versione (riprova)"
    if r.status_code == 422:
        return "richiesta rifiutata da GitHub"
    return f"risposta inattesa di GitHub (codice {r.status_code})"


def leggi_remoto(cfg, nome, http=None):
    """(contenuto|None, sha|None). File assente -> (None, None). Errori -> ErroreRemoto."""
    http = http or __import__("requests")
    try:
        r = http.get(_url(cfg, nome), headers=_intestazioni(cfg), params={"ref": cfg["branch"]}, timeout=TIMEOUT)
    except Exception as e:  # noqa: BLE001
        raise ErroreRemoto(f"rete non raggiungibile ({type(e).__name__})") from None
    if r.status_code == 404:
        # 404 può voler dire «file assente» (normale) o «repo/permessi sbagliati»
        try:
            msg = (r.json() or {}).get("message", "")
        except Exception:  # noqa: BLE001
            msg = ""
        if "Not Found" in msg and _repo_esiste(cfg, http) is False:
            raise ErroreRemoto(_spiega(r))
        return None, None
    if r.status_code != 200:
        raise ErroreRemoto(_spiega(r))
    try:
        j = r.json()
        sha = j.get("sha")
        if j.get("encoding") == "base64" and j.get("content"):
            return base64.b64decode(j["content"]), sha
        r2 = http.get(_url(cfg, nome), headers=_intestazioni(cfg, raw=True), params={"ref": cfg["branch"]}, timeout=TIMEOUT)
        if r2.status_code != 200:
            raise ErroreRemoto(_spiega(r2))
        return r2.content, sha
    except ErroreRemoto:
        raise
    except Exception as e:  # noqa: BLE001
        raise ErroreRemoto(f"risposta illeggibile ({type(e).__name__})") from None


def _repo_esiste(cfg, http):
    try:
        r = http.get(f"https://api.github.com/repos/{cfg['repo']}", headers=_intestazioni(cfg), timeout=TIMEOUT)
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return None


def scrivi_remoto(cfg, nome, contenuto, sha, messaggio, http=None):
    """Crea o aggiorna il file. Un solo nuovo tentativo se la versione è cambiata nel frattempo."""
    http = http or __import__("requests")
    for tentativo in range(2):
        corpo = {"message": messaggio, "content": base64.b64encode(contenuto).decode("ascii"), "branch": cfg["branch"]}
        if sha:
            corpo["sha"] = sha
        try:
            r = http.put(_url(cfg, nome), headers=_intestazioni(cfg), json=corpo, timeout=TIMEOUT)
        except Exception as e:  # noqa: BLE001
            raise ErroreRemoto(f"rete non raggiungibile ({type(e).__name__})") from None
        if r.status_code in (200, 201):
            return (r.json().get("content") or {}).get("sha")
        if r.status_code in (409, 422) and tentativo == 0:
            _, sha = leggi_remoto(cfg, nome, http)
            continue
        raise ErroreRemoto(_spiega(r))
    raise ErroreRemoto("conflitto di versione (riprova)")


# ------------------------------------------------------------------
# Operazioni di alto livello (non sollevano mai)
# ------------------------------------------------------------------


def _impronta_file(p):
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    except OSError:
        return None


def _impronta_db(p):
    """Impronta logica dell'archivio previsioni (non dei byte, che possono variare)."""
    try:
        import sqlite3

        con = sqlite3.connect(str(p), timeout=15)
        try:
            h = hashlib.sha256()
            for q in ("SELECT impronta FROM previsioni ORDER BY impronta",
                      "SELECT match_key, stato, gol_casa, gol_ospite FROM risultati ORDER BY match_key",
                      "SELECT batch_id FROM batches ORDER BY batch_id"):
                for riga in con.execute(q):
                    h.update(repr(tuple(riga)).encode())
            return h.hexdigest()
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        return None


def _registra_esito(nome, ok, messaggio):
    ss = _stato_sessione()
    esiti = ss.get("_br_esiti") or {}
    esiti[nome] = {"ok": ok, "messaggio": messaggio, "quando": time.strftime("%Y-%m-%d %H:%M:%S")}
    ss["_br_esiti"] = esiti


def ripristina_avvio(http=None):
    """Una volta per sessione: rimette sul disco i file mancanti dalla copia remota.

    Va chiamato PRIMA di ``persistenza.carica_avvio``. L'archivio previsioni si
    ripristina solo se quello locale è vuoto; gli altri due solo se il file manca.
    """
    ss = _stato_sessione()
    try:
        cfg = configurazione()
        if not cfg or ss.get("_br_init"):
            return
        ss["_br_init"] = True
        ss["_br_ok"] = {}
        for nome in NOMI:
            try:
                locale = percorso_locale(nome)
                if nome == "previsioni.db":
                    vuoto = (not locale.exists()) or DB.info_archivio(locale)["conteggi"]["previsioni"] == 0
                else:
                    vuoto = not locale.exists()
                dati, _sha = leggi_remoto(cfg, nome, http)
                ss["_br_ok"][nome] = True  # la lettura è riuscita (file presente o assente): si può caricare
                if dati is None or not vuoto:
                    _registra_esito(nome, True, "nessun ripristino necessario")
                    continue
                if nome == "previsioni.db":
                    agg = DB.unisci_backup(locale, dati)
                    _registra_esito(nome, True, f"ripristinate {agg.get('previsioni', 0)} previsioni dalla copia remota")
                else:
                    locale.parent.mkdir(parents=True, exist_ok=True)
                    tmp = locale.with_suffix(locale.suffix + ".tmp")
                    tmp.write_bytes(dati)
                    os.replace(tmp, locale)
                    ss.setdefault("_br_imp", {})[nome] = _impronta_file(locale)  # già identico al remoto
                    _registra_esito(nome, True, "ripristinato dalla copia remota")
            except ErroreRemoto as e:
                _registra_esito(nome, False, f"ripristino non riuscito: {e}")
            except Exception as e:  # noqa: BLE001
                log.exception("Ripristino remoto di %s fallito", nome)
                _registra_esito(nome, False, f"ripristino non riuscito: {type(e).__name__}")
    except Exception:  # noqa: BLE001
        log.exception("Ripristino remoto fallito")


def _dopo_errore(ss, nome):
    """Dopo un errore i file leggeri aspettano la pausa prima di ritentare: niente attese ripetute a ogni ricarica."""
    if nome != "previsioni.db":
        try:
            ss.setdefault("_br_ultimo", {})[nome] = time.time()
        except Exception:  # noqa: BLE001
            pass


def sincronizza(nome, forza=False, http=None):
    """Carica ``nome`` sul repository remoto. Ritorna (ok, messaggio); non solleva mai.

    previsioni.db: scarica → unisce → carica (mai sovrascrivere alla cieca).
    stato.json / registro CSV: solo se il ripristino è riuscito e con una pausa tra due caricamenti.
    """
    ss = _stato_sessione()
    try:
        cfg = configurazione()
        if not cfg:
            return False, "backup remoto non configurato"
        locale = percorso_locale(nome)
        if not locale.exists():
            return False, "niente da caricare"
        if nome != "previsioni.db":
            if not (ss.get("_br_ok") or {}).get(nome):
                msg = "non carico: il ripristino da remoto non è riuscito in questa sessione"
                _registra_esito(nome, False, msg)
                return False, msg
            ultimo = (ss.get("_br_ultimo") or {}).get(nome, 0)
            if not forza and time.time() - ultimo < PAUSA_FILE_LEGGERI:
                return False, "in attesa (pausa tra due caricamenti)"
            imp = _impronta_file(locale)
            if imp is not None and imp == (ss.get("_br_imp") or {}).get(nome):
                return True, "già aggiornato"
            dati = locale.read_bytes()
            _, sha = leggi_remoto(cfg, nome, http)
        else:
            remoto, sha = leggi_remoto(cfg, nome, http)  # se fallisce: ErroreRemoto, NON si carica
            if remoto is not None:
                DB.unisci_backup(locale, remoto)
            imp = _impronta_db(locale)
            if imp is not None and imp == (ss.get("_br_imp") or {}).get(nome) and not forza:
                return True, "già aggiornato"
            dati = DB.backup_bytes(locale)
        nuovo = scrivi_remoto(cfg, nome, dati, sha, f"backup {nome} {time.strftime('%Y-%m-%d %H:%M')}", http)
        ss.setdefault("_br_ultimo", {})[nome] = time.time()
        ss.setdefault("_br_imp", {})[nome] = imp
        _registra_esito(nome, True, "copia remota aggiornata")
        return True, "copia remota aggiornata"
    except ErroreRemoto as e:
        _dopo_errore(ss, nome)
        _registra_esito(nome, False, f"non riuscito: {e}")
        return False, f"non riuscito: {e}"
    except Exception as e:  # noqa: BLE001
        log.exception("Backup remoto di %s fallito", nome)
        _dopo_errore(ss, nome)
        _registra_esito(nome, False, f"non riuscito: {type(e).__name__}")
        return False, f"non riuscito: {type(e).__name__}"


def ripristina_ora(nome="previsioni.db", http=None):
    """Unisce la copia remota dell'archivio previsioni in quello locale (a richiesta). (ok, messaggio)."""
    try:
        cfg = configurazione()
        if not cfg:
            return False, "backup remoto non configurato"
        dati, _ = leggi_remoto(cfg, nome, http)
        if dati is None:
            return False, "sul repository non c'è ancora nessuna copia"
        agg = DB.unisci_backup(percorso_locale(nome), dati)
        return True, f"aggiunte {agg.get('previsioni', 0)} previsioni e {agg.get('risultati', 0)} risultati dalla copia remota"
    except ErroreRemoto as e:
        return False, f"non riuscito: {e}"
    except Exception as e:  # noqa: BLE001
        log.exception("Ripristino remoto a richiesta fallito")
        return False, f"non riuscito: {type(e).__name__}"


def stato():
    """Per la UI: configurato? e gli ultimi esiti per file."""
    ss = _stato_sessione()
    return {"configurato": configurazione() is not None, "esiti": dict(ss.get("_br_esiti") or {})}


ISTRUZIONI = """\
1. Su GitHub crea un repository **privato** (es. `b-betting-dati`) con un file README, così esiste il ramo `main`.
2. GitHub → Settings → Developer settings → Fine-grained tokens → Generate new token.
   Repository access: **solo** `b-betting-dati`. Permissions → Repository → **Contents: Read and write**.
   Scadenza: la più lunga consentita (a scadenza il backup smette di funzionare e l'app lo segnala).
3. Su Streamlit Community Cloud: la tua app → ⋮ → Settings → **Secrets**, incolla:

```
GITHUB_BACKUP_TOKEN = "github_pat_..."
GITHUB_BACKUP_REPO = "tuo-utente/b-betting-dati"
```

Non scrivere mai il token nel codice né nel repository dell'app (è pubblico).
"""
