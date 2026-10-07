"""Backup remoto opzionale su un repository GitHub PRIVATO.

Perché: su Streamlit Community Cloud il disco si azzera quando l'app si riavvia o va
in pausa. Senza una copia fuori dal disco, archivio previsioni, schedine e curve
sparirebbero. Qui la copia sta in un repository privato scelto dall'utente.

Si attiva SOLO se nei «Secrets» dell'app ci sono:
    GITHUB_BACKUP_TOKEN = "github_pat_..."        (permesso: Contents, lettura e scrittura, su quel solo repo)
    GITHUB_BACKUP_REPO  = "utente/nome-repo-privato"
    GITHUB_BACKUP_BRANCH = "main"                 (facoltativo)
Senza questi valori non succede nulla e resta il backup manuale.

MODELLO DI SCRITTURA (da leggere prima di cambiare qualcosa)
  * previsioni.db  -> più sessioni possono scriverlo: ogni caricamento è un ciclo
    «scarica → unisci → copia coerente → carica». Se GitHub risponde con un conflitto
    (qualcun altro ha caricato nel frattempo) il ciclo si RIFÀ da capo, con la copia
    remota nuova: non si ripete mai lo stesso contenuto già superato.
  * stato.json e registro CSV -> UNA sola sessione alla volta (single-writer): non
    esiste un'unione sicura di due versioni. Si carica solo se la copia remota è ancora
    quella vista all'avvio (o all'ultimo caricamento); altrimenti l'operazione fallisce
    in modo visibile e il remoto NON viene toccato.
  * La pausa di 2 minuti tra due caricamenti serve a non fare un commit a ogni clic. NON è
    un blocco e non impedisce a due sessioni di scrivere insieme.

STATO DEL FILE LOCALE all'avvio: ASSENTE, VALIDO o CORROTTO.
  * CORROTTO non vale come «presente»: il file viene messo da parte (mai cancellato) e,
    se esiste una copia remota valida, si ripristina da quella. Un file corrotto non viene
    mai caricato, né può far caricare uno stato vuoto al posto della copia buona.

Un upload riuscito non è un backup verificato; un backup verificato non è un restore riuscito.
Per questo ogni caricamento aggiorna anche ``manifest.json`` (data, impronta, conteggi,
versione) e l'interfaccia distingue: ultimo download manuale, ultima copia remota
CONFERMATA, ultimo ripristino.

Altre regole: nessuna funzione pubblica solleva; il token non compare mai in messaggi o log.
"""

import base64
import hashlib
import io
import json
import logging
import os
import sqlite3
import time
from pathlib import Path

import persistenza
import previsioni_db as DB

log = logging.getLogger("b-betting")

CARTELLA_REMOTA = "b-betting"
TIMEOUT = (5, 20)
PAUSA_FILE_LEGGERI = 120  # secondi tra due caricamenti di stato.json / registro CSV
TENTATIVI_DB = 3

NOMI = ("previsioni.db", "stato.json", "registro_pronostici.csv")
MANIFEST = "manifest.json"

ASSENTE, VALIDO, CORROTTO = "assente", "valido", "corrotto"


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
# Validazione del contenuto (locale e remoto)
# ------------------------------------------------------------------

COLONNE_REGISTRO = ("campionato", "data", "squadra1", "squadra2", "giocata")


def contenuto_valido(nome, dati):
    """True se ``dati`` (bytes) è un file di quel tipo, leggibile e completo."""
    try:
        if not dati:
            return False
        if nome == "stato.json":
            d = json.loads(dati.decode("utf-8"))
            return isinstance(d, dict) and "versione" in d
        if nome == "registro_pronostici.csv":
            import pandas as pd

            df = pd.read_csv(io.BytesIO(dati), dtype=str)
            return all(c in df.columns for c in COLONNE_REGISTRO)
        if nome == "previsioni.db":
            import tempfile

            if dati[:16] != b"SQLite format 3\x00":
                return False
            fd, tmp = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            try:
                Path(tmp).write_bytes(dati)
                con = sqlite3.connect(tmp)
                try:
                    if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        return False
                    tab = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                finally:
                    con.close()
                return all(t in tab for t in DB.TABELLE)
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
    except Exception:  # noqa: BLE001
        return False
    return False


def stato_locale(nome):
    """ASSENTE, VALIDO o CORROTTO per il file locale di ``nome``."""
    p = percorso_locale(nome)
    if not p.exists():
        return ASSENTE
    try:
        return VALIDO if contenuto_valido(nome, p.read_bytes()) else CORROTTO
    except OSError:
        return CORROTTO


def _metti_da_parte(p):
    """Rinomina un file corrotto senza cancellarlo. Ritorna il nuovo nome (o None)."""
    nuovo = p.with_name(f"{p.stem}.corrotto-{time.strftime('%Y%m%d-%H%M%S')}{p.suffix}")
    try:
        os.replace(p, nuovo)
        return nuovo.name
    except OSError:
        return None


# ------------------------------------------------------------------
# API GitHub (contents)
# ------------------------------------------------------------------


class ErroreRemoto(Exception):
    """Errore di rete o di GitHub, con un messaggio leggibile e senza segreti."""


class ConflittoRemoto(ErroreRemoto):
    """La copia remota è cambiata rispetto a quella su cui si basava il caricamento."""


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
        return "conflitto di versione"
    if r.status_code == 422:
        return "richiesta rifiutata da GitHub"
    return f"risposta inattesa di GitHub (codice {r.status_code})"


def _http(http):
    return http or __import__("requests")


def _repo_esiste(cfg, http):
    try:
        r = http.get(f"https://api.github.com/repos/{cfg['repo']}", headers=_intestazioni(cfg), timeout=TIMEOUT)
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return None


def leggi_remoto(cfg, nome, http=None):
    """(contenuto|None, sha|None). File assente -> (None, None). Errori -> ErroreRemoto."""
    http = _http(http)
    try:
        r = http.get(_url(cfg, nome), headers=_intestazioni(cfg), params={"ref": cfg["branch"]}, timeout=TIMEOUT)
    except Exception as e:  # noqa: BLE001
        raise ErroreRemoto(f"rete non raggiungibile ({type(e).__name__})") from None
    if r.status_code == 404:
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


def sha_git(contenuto):
    """SHA che git assegna a un file con questo contenuto (è quello che GitHub restituisce)."""
    return hashlib.sha1(b"blob %d\0" % len(contenuto) + contenuto).hexdigest()


def scrivi_remoto(cfg, nome, contenuto, sha, messaggio, http=None):
    """UNA sola scrittura. Se la versione remota non è più ``sha`` -> ConflittoRemoto.

    Nessun nuovo tentativo qui dentro: ripetere lo stesso contenuto dopo un conflitto
    significherebbe sovrascrivere ciò che l'altra sessione ha caricato.
    """
    http = _http(http)
    corpo = {"message": messaggio, "content": base64.b64encode(contenuto).decode("ascii"), "branch": cfg["branch"]}
    if sha:
        corpo["sha"] = sha
    try:
        r = http.put(_url(cfg, nome), headers=_intestazioni(cfg), json=corpo, timeout=TIMEOUT)
    except Exception as e:  # noqa: BLE001
        raise ErroreRemoto(f"rete non raggiungibile ({type(e).__name__})") from None
    if r.status_code in (200, 201):
        try:
            salvato = (r.json().get("content") or {}).get("sha")
        except Exception:  # noqa: BLE001
            salvato = None
        # «caricamento riuscito» non basta: GitHub deve aver salvato ESATTAMENTE i nostri byte
        if salvato != sha_git(contenuto):
            raise ErroreRemoto("GitHub ha risposto, ma la copia salvata non corrisponde a quella inviata")
        return salvato
    if r.status_code in (409, 422):
        raise ConflittoRemoto(_spiega(r))
    raise ErroreRemoto(_spiega(r))


# ------------------------------------------------------------------
# Impronte e manifest
# ------------------------------------------------------------------


def _sha256(dati):
    return hashlib.sha256(dati).hexdigest()


def _impronta_file(p):
    try:
        return _sha256(Path(p).read_bytes())
    except OSError:
        return None


def _impronta_db(p):
    """Impronta logica dell'archivio previsioni (non dei byte, che possono variare)."""
    try:
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


def _impronta_locale(nome):
    p = percorso_locale(nome)
    if not p.exists():
        return None
    return _impronta_db(p) if nome == "previsioni.db" else _impronta_file(p)


def _info_per_manifest(nome, dati):
    p = percorso_locale(nome)
    info = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sha256": _sha256(dati),
        "dimensione": len(dati),
        "impronta": _impronta_locale(nome),
    }
    try:
        from previsioni_batch import VERSIONE_APP

        info["versione_app"] = VERSIONE_APP
    except Exception:  # noqa: BLE001
        pass
    if nome == "previsioni.db":
        try:
            info["schema"] = DB.SCHEMA_VERSIONE
            info["conteggi"] = DB.info_archivio(p)["conteggi"]
        except Exception:  # noqa: BLE001
            pass
    return info


def _leggi_manifest(cfg, http=None):
    dati, sha = leggi_remoto(cfg, MANIFEST, http)
    if dati is None:
        return {"versione": 1, "file": {}}, sha
    try:
        m = json.loads(dati.decode("utf-8"))
        if isinstance(m, dict) and isinstance(m.get("file"), dict):
            return m, sha
    except Exception:  # noqa: BLE001
        pass
    raise ErroreRemoto("manifest remoto illeggibile")


def _aggiorna_manifest(cfg, nome, info, http=None):
    """Aggiorna la voce di ``nome`` nel manifest (unione per chiave: il retry rilegge e riunisce)."""
    for _ in range(3):
        m, sha = _leggi_manifest(cfg, http)
        m["file"][nome] = info
        try:
            scrivi_remoto(cfg, MANIFEST, json.dumps(m, indent=1, sort_keys=True).encode("utf-8"), sha,
                          f"manifest {nome} {info['utc']}", http)
            return True
        except ConflittoRemoto:
            continue
    return False


# ------------------------------------------------------------------
# Esiti della sessione
# ------------------------------------------------------------------


def _registra_esito(nome, ok, messaggio):
    ss = _stato_sessione()
    esiti = ss.get("_br_esiti") or {}
    esiti[nome] = {"ok": ok, "messaggio": messaggio, "quando": time.strftime("%Y-%m-%d %H:%M:%S")}
    ss["_br_esiti"] = esiti


def _dopo_errore(ss, nome):
    """Dopo un errore i file leggeri aspettano la pausa prima di ritentare: niente attese ripetute a ogni ricarica."""
    if nome != "previsioni.db":
        try:
            ss.setdefault("_br_ultimo", {})[nome] = time.time()
        except Exception:  # noqa: BLE001
            pass


# ------------------------------------------------------------------
# Ripristino all'avvio
# ------------------------------------------------------------------


def _ripristina_file(nome, dati):
    locale = percorso_locale(nome)
    if nome == "previsioni.db":
        agg = DB.unisci_backup(locale, dati)
        return f"ripristinate {agg.get('previsioni', 0)} previsioni dalla copia remota"
    locale.parent.mkdir(parents=True, exist_ok=True)
    tmp = locale.with_suffix(locale.suffix + ".tmp")
    tmp.write_bytes(dati)
    os.replace(tmp, locale)
    _stato_sessione().setdefault("_br_imp", {})[nome] = _impronta_file(locale)  # ora identico al remoto
    return "ripristinato dalla copia remota"


def ripristina_avvio(http=None):
    """Una volta per sessione. Va chiamato PRIMA di ``persistenza.carica_avvio``.

    Per ogni file: stato locale ASSENTE / VALIDO / CORROTTO e copia remota valida o no.
      * ASSENTE + remoto valido -> ripristina;
      * CORROTTO -> lo mette da parte (mai cancellato); se il remoto è valido ripristina da lì;
      * VALIDO -> nulla (l'archivio previsioni, se vuoto, riceve comunque il remoto);
      * remoto presente ma NON valido -> non si usa e non si sovrascrive (i caricamenti restano bloccati).
    """
    ss = _stato_sessione()
    try:
        cfg = configurazione()
        if not cfg or ss.get("_br_init"):
            return
        ss["_br_init"] = True
        ss["_br_ok"], ss["_br_sha"] = {}, {}
        for nome in NOMI:
            try:
                locale = percorso_locale(nome)
                stato = stato_locale(nome)
                dati, sha = leggi_remoto(cfg, nome, http)
                ss["_br_sha"][nome] = sha
                remoto_ok = dati is not None and contenuto_valido(nome, dati)
                if dati is not None and not remoto_ok:
                    ss["_br_ok"][nome] = False  # non si sovrascrive una copia remota che non si capisce
                    if stato == CORROTTO:
                        _metti_da_parte(locale)
                    _registra_esito(nome, False, "la copia remota non è valida: non la uso e non la sovrascrivo")
                    continue
                ss["_br_ok"][nome] = True
                messaggio = "nessun ripristino necessario"
                aside = None
                if stato == CORROTTO:
                    aside = _metti_da_parte(locale)
                    messaggio = f"file locale corrotto messo da parte ({aside or 'rinomina non riuscita'})"
                    if aside is None:
                        ss["_br_ok"][nome] = False  # non si può isolare: meglio non caricare niente
                        _registra_esito(nome, False, messaggio)
                        continue
                if remoto_ok:
                    vuoto = stato in (ASSENTE, CORROTTO)
                    if nome == "previsioni.db" and stato == VALIDO:
                        vuoto = DB.info_archivio(locale)["conteggi"]["previsioni"] == 0
                    if vuoto:
                        messaggio = (messaggio + "; " if aside else "") + _ripristina_file(nome, dati)
                _registra_esito(nome, True, messaggio)
            except ErroreRemoto as e:
                _registra_esito(nome, False, f"ripristino non riuscito: {e}")
            except Exception as e:  # noqa: BLE001
                log.exception("Ripristino remoto di %s fallito", nome)
                _registra_esito(nome, False, f"ripristino non riuscito: {type(e).__name__}")
    except Exception:  # noqa: BLE001
        log.exception("Ripristino remoto fallito")


# ------------------------------------------------------------------
# Caricamento
# ------------------------------------------------------------------


def _carica_db(cfg, locale, forza, http):
    """Ciclo scarica → unisci → copia → carica, rifatto da capo dopo ogni conflitto."""
    ss = _stato_sessione()
    nome = "previsioni.db"
    for _ in range(TENTATIVI_DB):
        remoto, sha = leggi_remoto(cfg, nome, http)  # se fallisce: ErroreRemoto, NON si carica
        if remoto is not None:
            if not contenuto_valido(nome, remoto):
                raise ErroreRemoto("la copia remota non è valida: non la sovrascrivo")
            DB.unisci_backup(locale, remoto)
        imp = _impronta_db(locale)
        if not forza and remoto is not None and imp is not None and imp == (ss.get("_br_imp") or {}).get(nome):
            return True, "già aggiornato"
        dati = DB.backup_bytes(locale)
        try:
            scrivi_remoto(cfg, nome, dati, sha, f"backup {nome} {time.strftime('%Y-%m-%d %H:%M')}", http)
        except ConflittoRemoto:
            continue  # un'altra sessione ha caricato nel frattempo: si riparte dalla sua versione
        ss.setdefault("_br_imp", {})[nome] = imp
        ss.setdefault("_br_ultimo", {})[nome] = time.time()
        manifest_ok = _aggiorna_manifest(cfg, nome, _info_per_manifest(nome, dati), http)
        msg = "copia remota aggiornata" + ("" if manifest_ok else " (manifest non aggiornato)")
        return True, msg
    raise ConflittoRemoto("conflitti ripetuti: un'altra sessione sta scrivendo, riprova tra poco")


def _carica_file(cfg, nome, locale, forza, http):
    """stato.json / registro CSV: single-writer con controllo della versione remota conosciuta."""
    ss = _stato_sessione()
    if not (ss.get("_br_ok") or {}).get(nome):
        msg = "non carico: il ripristino da remoto non è riuscito in questa sessione"
        _registra_esito(nome, False, msg)
        return False, msg
    dati = locale.read_bytes()
    if not contenuto_valido(nome, dati):
        msg = "non carico: il file locale non è valido (corrotto o incompleto)"
        _registra_esito(nome, False, msg)
        return False, msg
    ultimo = (ss.get("_br_ultimo") or {}).get(nome, 0)
    if not forza and time.time() - ultimo < PAUSA_FILE_LEGGERI:
        return False, "in attesa (pausa tra due caricamenti)"
    imp = _sha256(dati)
    if imp == (ss.get("_br_imp") or {}).get(nome):
        return True, "già aggiornato"
    _, sha_attuale = leggi_remoto(cfg, nome, http)
    if sha_attuale != (ss.get("_br_sha") or {}).get(nome):
        raise ConflittoRemoto("la copia remota è stata modificata da un'altra sessione: non la sovrascrivo")
    nuovo = scrivi_remoto(cfg, nome, dati, sha_attuale, f"backup {nome} {time.strftime('%Y-%m-%d %H:%M')}", http)
    ss.setdefault("_br_sha", {})[nome] = nuovo
    ss.setdefault("_br_imp", {})[nome] = imp
    ss.setdefault("_br_ultimo", {})[nome] = time.time()
    manifest_ok = _aggiorna_manifest(cfg, nome, _info_per_manifest(nome, dati), http)
    return True, "copia remota aggiornata" + ("" if manifest_ok else " (manifest non aggiornato)")


def sincronizza(nome, forza=False, http=None):
    """Carica ``nome`` sul repository remoto. Ritorna (ok, messaggio); non solleva mai."""
    ss = _stato_sessione()
    try:
        cfg = configurazione()
        if not cfg:
            return False, "backup remoto non configurato"
        locale = percorso_locale(nome)
        if not locale.exists():
            return False, "niente da caricare"
        if nome == "previsioni.db":
            if stato_locale(nome) != VALIDO:
                msg = "non carico: l'archivio locale non è valido"
                _registra_esito(nome, False, msg)
                return False, msg
            ok, msg = _carica_db(cfg, locale, forza, http)
        else:
            ok, msg = _carica_file(cfg, nome, locale, forza, http)
        if ok:
            _registra_esito(nome, True, msg)
        return ok, msg
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
        if not contenuto_valido(nome, dati):
            return False, "la copia remota non è valida: non la uso"
        agg = DB.unisci_backup(percorso_locale(nome), dati)
        return True, f"aggiunte {agg.get('previsioni', 0)} previsioni e {agg.get('risultati', 0)} risultati dalla copia remota"
    except ErroreRemoto as e:
        return False, f"non riuscito: {e}"
    except Exception as e:  # noqa: BLE001
        log.exception("Ripristino remoto a richiesta fallito")
        return False, f"non riuscito: {type(e).__name__}"


# ------------------------------------------------------------------
# Stato per l'interfaccia
# ------------------------------------------------------------------


def stato():
    """Per la UI: configurato? e gli ultimi esiti della sessione per file."""
    ss = _stato_sessione()
    return {"configurato": configurazione() is not None, "esiti": dict(ss.get("_br_esiti") or {})}


def stato_copia(http=None):
    """Confronta i dati locali con l'ULTIMA copia remota CONFERMATA dal manifest.

    Ritorna ``{nome: {"remoto": voce|None, "allineata": bool|None}}`` oppure
    ``{"errore": messaggio}``. ``allineata=False`` = esiste un cambiamento locale che
    la copia durevole non contiene («copia durevole non confermata»).
    """
    try:
        cfg = configurazione()
        if not cfg:
            return {"errore": "backup remoto non configurato"}
        m, _ = _leggi_manifest(cfg, http)
        out = {}
        for nome in NOMI:
            voce = m["file"].get(nome)
            loc = _impronta_locale(nome)
            if loc is None:
                out[nome] = {"remoto": voce, "allineata": None}  # niente di locale da confrontare
            else:
                out[nome] = {"remoto": voce, "allineata": bool(voce) and voce.get("impronta") == loc}
        return out
    except ErroreRemoto as e:
        return {"errore": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"errore": f"non riuscito: {type(e).__name__}"}


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
