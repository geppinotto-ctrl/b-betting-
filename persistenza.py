"""Persistenza su file: archivio schedine, schedina in corso e curve calibrate.

Fino a ieri tutto viveva in ``st.session_state`` e spariva a ogni riavvio.
Ora lo stato importante viene salvato in un unico file JSON.

Regole:
  * dove: cartella ``dati_utente`` accanto ai sorgenti, oppure quella indicata
    dalla variabile d'ambiente ``B_BETTING_DATI``;
  * scrittura atomica (file temporaneo + ``os.replace``): un crash a metà non
    lascia mai un file a metà. La versione precedente resta in ``stato.prev.json``;
  * un file illeggibile non viene mai cancellato né sovrascritto: viene
    rinominato ``stato.corrotto-<data>.json`` e l'app riparte pulita;
  * nessuna funzione pubblica solleva: un disco pieno o in sola lettura non
    deve fermare l'app, ma l'errore viene mostrato nella barra laterale;
  * si scrive solo se qualcosa è cambiato (impronta del contenuto).

Limite: il file è uno solo e vale per tutte le sessioni. Va bene per un uso
personale; se l'app fosse aperta da più persone, l'ultimo salvataggio vince.
"""

import hashlib
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

log = logging.getLogger("b-betting")

NOME_FILE = "stato.json"
VERSIONE = 1
CHIAVI_UTILE = ("1x2", "over", "goal")


def cartella():
    base = os.environ.get("B_BETTING_DATI", "").strip()
    return Path(base) if base else Path(__file__).resolve().parent / "dati_utente"


def percorso():
    return cartella() / NOME_FILE


# ------------------------------------------------------------------
# Conversione stato <-> dati serializzabili (logica pura)
# ------------------------------------------------------------------


def _slip_in_righe(df):
    """DataFrame della schedina in corso -> lista di dizionari JSON-safe."""
    if df is None or not hasattr(df, "to_dict") or len(df) == 0:
        return []
    righe = []
    for r in df.to_dict("records"):
        try:
            quota = float(r.get("Quota"))
        except (TypeError, ValueError):
            continue
        if quota != quota:  # NaN
            continue
        righe.append({
            "Partita": str(r.get("Partita", "")),
            "Giocata": str(r.get("Giocata", "")),
            "Quota": quota,
            "Vinta": bool(r.get("Vinta", False)),
            "Elimina": False,
        })
    return righe


def estrai(stato):
    """Ricava dallo stato di sessione i dati da salvare."""
    arch = stato.get("slip_arch") or []
    calib = stato.get("calib") or {}
    return {
        "versione": VERSIONE,
        "slip_arch": list(arch),
        "slip_df": _slip_in_righe(stato.get("slip_df")),
        "calib": dict(calib),
        "usa_calib": bool(stato.get("usa_calib", False)),
    }


def pulisci_archivio(lista):
    """Tiene solo le schedine ben formate (stesso criterio dell'importazione)."""
    if not isinstance(lista, list):
        return []
    visti, out = set(), []
    for a in lista:
        if not isinstance(a, dict) or not a.get("id") or "puntata" not in a:
            continue
        if a["id"] in visti:
            continue
        visti.add(a["id"])
        out.append(a)
    return out


def pulisci_calibrazione(calib):
    """Tiene solo le calibrazioni complete: una curva rotta non deve mai arrivare ai calcoli."""
    if not isinstance(calib, dict):
        return {}
    out = {}
    for torneo, c in calib.items():
        try:
            if not isinstance(c, dict):
                continue
            curve, utile = c["curve"], c["utile"]
            if not isinstance(curve, dict) or not isinstance(utile, dict):
                continue
            if not all(k in utile for k in CHIAVI_UTILE):
                continue
            if not all(k in curve for k in ("1", "X", "2", "over", "goal")):
                continue
            for nome, cur in curve.items():
                if cur is not None and (
                    not isinstance(cur, dict)
                    or len(cur.get("x", [])) != len(cur.get("y", []))
                ):
                    raise ValueError(f"curva {nome} incoerente")
            out[str(torneo)] = {
                "curve": curve,
                "utile": {k: bool(utile[k]) for k in CHIAVI_UTILE},
                "n_fit": int(c["n_fit"]),
                "n_test": int(c.get("n_test", 0)),
                "prima_dopo": {
                    k: [float(v[0]), float(v[1])] for k, v in c["prima_dopo"].items()
                },
            }
        except Exception:  # noqa: BLE001 - una voce rotta non blocca le altre
            log.warning("Calibrazione di %r scartata: dati incompleti", torneo)
    return out


def ripristina(dati, stato):
    """Rimette in ``stato`` i dati letti dal file (dopo averli ripuliti)."""
    if not isinstance(dati, dict):
        return
    arch = pulisci_archivio(dati.get("slip_arch"))
    if arch:
        stato["slip_arch"] = arch
    calib = pulisci_calibrazione(dati.get("calib"))
    if calib:
        stato["calib"] = calib
        stato["usa_calib"] = bool(dati.get("usa_calib", False))
    righe = dati.get("slip_df")
    if isinstance(righe, list) and righe:
        import pandas as pd

        validi = [
            r for r in righe
            if isinstance(r, dict) and isinstance(r.get("Quota"), (int, float))
        ]
        if validi:
            stato["slip_df"] = pd.DataFrame({
                "Partita": pd.Series([str(r.get("Partita", "")) for r in validi], dtype="object"),
                "Giocata": pd.Series([str(r.get("Giocata", "")) for r in validi], dtype="object"),
                "Quota": pd.Series([float(r["Quota"]) for r in validi], dtype="float"),
                "Vinta": pd.Series([bool(r.get("Vinta", False)) for r in validi], dtype="bool"),
                "Elimina": pd.Series([False] * len(validi), dtype="bool"),
            })


def impronta(dati):
    testo = json.dumps(dati, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------
# File
# ------------------------------------------------------------------


def scrivi(dati, dove=None):
    """Scrittura atomica, conservando la versione precedente."""
    dove = Path(dove) if dove else percorso()
    dove.parent.mkdir(parents=True, exist_ok=True)
    testo = json.dumps(dati, ensure_ascii=False, indent=1, default=str)
    json.loads(testo)  # se non si rilegge, non si scrive
    fd, tmp = tempfile.mkstemp(dir=str(dove.parent), prefix=".stato-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(testo)
            f.flush()
            os.fsync(f.fileno())
        if dove.exists():
            shutil.copy2(dove, dove.with_name(dove.stem + ".prev.json"))
        os.replace(tmp, dove)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def leggi(dove=None):
    """(dati, messaggio). File assente -> (None, ""). File rotto -> messo da parte."""
    dove = Path(dove) if dove else percorso()
    if not dove.exists():
        return None, ""
    try:
        dati = json.loads(dove.read_text(encoding="utf-8"))
        if not isinstance(dati, dict):
            raise ValueError("il file non contiene un oggetto JSON")
        return dati, ""
    except Exception as e:  # noqa: BLE001
        sposta = dove.with_name(
            f"{dove.stem}.corrotto-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        try:
            os.replace(dove, sposta)
            dove_e = f"Il file dei dati era illeggibile ({type(e).__name__}): l'ho messo da parte come {sposta.name}."
        except OSError:
            dove_e = f"Il file dei dati è illeggibile ({type(e).__name__}) e non sono riuscito a metterlo da parte."
        return None, dove_e


# ------------------------------------------------------------------
# Collegamento con Streamlit (mai solleva)
# ------------------------------------------------------------------


def carica_avvio():
    """Da chiamare all'inizio di ogni esecuzione: carica il file una volta per sessione."""
    try:
        import streamlit as st

        ss = st.session_state
        if ss.get("_persist_init"):
            return
        ss["_persist_init"] = True
        dati, msg = leggi()
        if msg:
            ss["_persist_msg"] = msg
        if dati:
            ripristina(dati, ss)
        ss["_persist_hash"] = impronta(estrai(ss))
    except Exception as e:  # noqa: BLE001
        log.exception("Caricamento dati salvati fallito")
        try:
            import streamlit as st

            st.session_state["_persist_errore"] = f"{type(e).__name__}: {e}"
        except Exception:  # noqa: BLE001
            pass


def salva_se_cambiato():
    """Salva su file se lo stato è cambiato. Ritorna True se ha scritto."""
    try:
        import streamlit as st

        ss = st.session_state
        if not ss.get("_persist_init"):
            return False  # prima si carica: salvare uno stato vuoto cancellerebbe tutto
        dati = estrai(ss)
        h = impronta(dati)
        if h == ss.get("_persist_hash"):
            return False
        scrivi(dati)
        ss["_persist_hash"] = h
        ss.pop("_persist_errore", None)
        return True
    except Exception as e:  # noqa: BLE001
        log.exception("Salvataggio dati fallito")
        try:
            import streamlit as st

            st.session_state["_persist_errore"] = f"{type(e).__name__}: {e}"
        except Exception:  # noqa: BLE001
            pass
        return False


def mostra_stato_salvataggio():
    """Piccolo stato nella barra laterale: salvato, oppure cosa non va."""
    import streamlit as st

    ss = st.session_state
    if ss.get("_persist_msg"):
        st.warning(ss["_persist_msg"])
    if ss.get("_persist_errore"):
        st.error(
            "💾 Salvataggio su file non riuscito: " + str(ss["_persist_errore"])
            + ". I dati restano in memoria, ma si perdono se l'app si riavvia. "
            "Usa «Backup e importazione» nella Schedina."
        )
    else:
        st.caption(f"💾 Dati salvati in {cartella()}")
