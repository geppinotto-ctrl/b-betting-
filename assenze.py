"""Assenze (infortuni, squalifiche, dubbi) -> correzione dei gol attesi.

Budget zero: la fonte è il file `assenze.csv`, che aggiorni a mano (anche dal
pannello nella barra laterale) o con uno script. Nessuna API a pagamento.

Come funziona
-------------
Per ogni giocatore assente si indica quanto pesa sulla propria squadra:
  peso_att  quota 0-1 dei gol/occasioni della squadra che passa da lui
            (es. 0.30 = prima punta che garantisce circa il 30% dell'attacco)
  peso_dif  importanza 0-1 per la difesa (es. portiere titolare o centrale
            insostituibile)
La perdita è  K * peso * gravità_stato  (infortunato/squalificato = 1,
dubbio = 0.5), sommata sui giocatori della squadra e limitata a TETTO.
  attacco:  λ_squadra  × (1 - perdita_att)
  difesa:   λ_avversario × (1 + perdita_dif)

ATTENZIONE: K, TETTO e i pesi sono stime ragionate, NON calibrate: non
esiste uno storico delle assenze con cui fare un backtest. Per questo la
correzione è piccola, limitata e spenta di default. Le assenze lunghe
sono in parte già "dentro" le forze del modello (derivano dai risultati
recenti): non inserire giocatori fuori da molte settimane.
"""

import difflib
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from config import adesso
from quote import _canon_squadra
from resilienza import svuota_cache

log = logging.getLogger("b-betting")

FILE_ASSENZE = Path(__file__).parent / "assenze.csv"
COLONNE = ["squadra", "giocatore", "ruolo", "stato", "peso_att", "peso_dif", "aggiornato", "nota"]
RUOLI = ["POR", "DIF", "CEN", "ATT"]
STATI = ["Infortunato", "Squalificato", "Dubbio", "OK"]
GRAVITA = {"infortunato": 1.0, "squalificato": 1.0, "dubbio": 0.5, "ok": 0.0}

K = 0.35  # quanta parte del peso si traduce in gol attesi persi
TETTO = 0.12  # perdita massima per squadra (12%) su attacco e su difesa
ETA_MAX_GIORNI = 21  # informazioni più vecchie vengono ignorate
SOGLIA_NOME = 0.85


def _vuoto():
    return pd.DataFrame(columns=COLONNE)


def _oggi():
    try:
        return adesso().date()
    except Exception:
        return date.today()


def pulisci_assenze(df, oggi=None, eta_max=ETA_MAX_GIORNI):
    """Normalizza il DataFrame e scarta righe non valide, vecchie o 'OK'."""
    if df is None or len(df) == 0:
        return _vuoto()
    oggi = oggi or _oggi()
    d = df.copy()
    for c in COLONNE:
        if c not in d.columns:
            d[c] = None
    d = d[COLONNE]
    d = d.dropna(subset=["squadra", "giocatore", "stato"])
    d["stato"] = d["stato"].astype(str).str.strip()
    d["gravita"] = d["stato"].str.lower().map(GRAVITA)
    d = d[d["gravita"].notna() & (d["gravita"] > 0)]
    for c in ("peso_att", "peso_dif"):
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    data = pd.to_datetime(d["aggiornato"], errors="coerce").dt.date
    # data mancante = aggiornata oggi (si compila al salvataggio dal pannello)
    data = data.where(data.notna(), oggi)
    eta = data.map(lambda x: (oggi - x).days)
    d = d[(eta <= eta_max) & (eta >= -1)]
    d["chiave"] = d["squadra"].map(_canon_squadra)
    return d.reset_index(drop=True)


def leggi_csv(percorso=FILE_ASSENZE):
    percorso = Path(percorso)
    if not percorso.exists():
        return _vuoto()
    try:
        return pd.read_csv(percorso, comment="#", skip_blank_lines=True)
    except Exception:
        return _vuoto()


def salva_csv(df, percorso=FILE_ASSENZE):
    """Salva le assenze; le righe senza data ricevono quella di oggi."""
    d = df.copy()
    for c in COLONNE:
        if c not in d.columns:
            d[c] = None
    d = d[COLONNE].dropna(subset=["squadra", "giocatore"], how="any")
    oggi = _oggi().isoformat()
    d["aggiornato"] = d["aggiornato"].fillna(oggi).replace("", oggi)
    d.to_csv(percorso, index=False)


@st.cache_data(show_spinner=False)
def _carica_cached(mtime, giorno):
    # mtime e giorno servono solo a invalidare la cache quando il file
    # cambia o passa la mezzanotte (le assenze "scadono").
    return pulisci_assenze(leggi_csv(), oggi=giorno)


def assenze_attive():
    """DataFrame delle assenze valide, o None se la correzione è spenta."""
    if not st.session_state.get("usa_assenze", False):
        return None
    try:
        mtime = FILE_ASSENZE.stat().st_mtime if FILE_ASSENZE.exists() else 0
    except OSError:
        mtime = 0
    try:
        return _carica_cached(mtime, _oggi())
    except Exception:  # noqa: BLE001 - un CSV rovinato non deve fermare i pronostici
        log.exception("assenze.csv non elaborabile: correzione disattivata")
        return _vuoto()


def _righe_squadra(df, squadra):
    if df is None or len(df) == 0:
        return df.iloc[0:0] if df is not None else _vuoto()
    k = _canon_squadra(squadra)
    esatte = df[df["chiave"] == k]
    if len(esatte):
        return esatte
    simili = [
        c for c in df["chiave"].unique()
        if difflib.SequenceMatcher(None, k, c).ratio() >= SOGLIA_NOME
    ]
    return df[df["chiave"].isin(simili)]


def fattori_squadra(df, squadra):
    """(fattore attacco <=1, fattore 'gol subiti' >=1, elenco assenti)."""
    righe = _righe_squadra(df, squadra)
    if len(righe) == 0:
        return 1.0, 1.0, []
    perd_att = min(TETTO, K * float((righe["peso_att"] * righe["gravita"]).sum()))
    perd_dif = min(TETTO, K * float((righe["peso_dif"] * righe["gravita"]).sum()))
    elenco = [f"{r.giocatore} ({r.stato.lower()})" for r in righe.itertuples()]
    return 1.0 - perd_att, 1.0 + perd_dif, elenco


def applica_assenze(l1, l2, t1, t2, df):
    """Corregge i gol attesi. Restituisce (l1, l2, info).

    info = {'attivo': bool, 'casa': [...], 'ospite': [...], 'l1_orig', 'l2_orig'}
    """
    info = {"attivo": False, "casa": [], "ospite": [], "l1_orig": l1, "l2_orig": l2}
    if df is None or len(df) == 0:
        return l1, l2, info
    a1, d1, el1 = fattori_squadra(df, t1)
    a2, d2, el2 = fattori_squadra(df, t2)
    if not el1 and not el2:
        return l1, l2, info
    info.update({"attivo": True, "casa": el1, "ospite": el2})
    return l1 * a1 * d2, l2 * a2 * d1, info


def descrivi(t1, t2, df):
    """Testo breve da mostrare sotto il pronostico (stringa vuota se nulla)."""
    _, _, info = applica_assenze(1.0, 1.0, t1, t2, df)
    if not info["attivo"]:
        return ""
    parti = []
    if info["casa"]:
        parti.append(f"{t1}: " + ", ".join(info["casa"]))
    if info["ospite"]:
        parti.append(f"{t2}: " + ", ".join(info["ospite"]))
    return "Assenze considerate — " + " | ".join(parti)


def pannello_assenze():
    """Interruttore e tabella modificabile, da chiamare nella barra laterale."""
    st.checkbox(
        "Considera assenze (sperimentale)",
        key="usa_assenze",
        value=False,
        on_change=lambda: svuota_cache("calcoli"),
        help="Corregge i gol attesi delle partite FUTURE in base a assenze.csv. "
        "Non influenza il backtest. Pesi non calibrati: effetto piccolo e limitato.",
    )
    if not st.session_state.get("usa_assenze", False):
        return
    with st.expander("✏️ Modifica assenze"):
        base = leggi_csv()
        if len(base) == 0:
            base = _vuoto()
        modificata = st.data_editor(
            base,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            column_config={
                "ruolo": st.column_config.SelectboxColumn("ruolo", options=RUOLI),
                "stato": st.column_config.SelectboxColumn("stato", options=STATI),
                "peso_att": st.column_config.NumberColumn("peso_att", min_value=0.0, max_value=1.0, step=0.05),
                "peso_dif": st.column_config.NumberColumn("peso_dif", min_value=0.0, max_value=1.0, step=0.05),
            },
            key="editor_assenze",
        )
        st.caption(
            "peso_att / peso_dif: quota 0-1 che il giocatore vale per attacco / "
            f"difesa della squadra. Righe più vecchie di {ETA_MAX_GIORNI} giorni "
            "vengono ignorate. Se l'app gira su un servizio con disco temporaneo, "
            "scarica il file prima di spegnere."
        )
        if st.button("💾 Salva assenze", use_container_width=True):
            try:
                salva_csv(modificata)
            except OSError as e:
                st.error(f"❌ Impossibile salvare assenze.csv ({e}). Il disco potrebbe essere in sola lettura.")
            except Exception as e:  # noqa: BLE001
                st.error(f"❌ Assenze non salvate: {type(e).__name__}. Controlla i valori inseriti.")
            else:
                svuota_cache("calcoli")
                st.rerun()
