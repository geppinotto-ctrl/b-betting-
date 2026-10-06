"""Registro dei pronostici: la prova sul campo del modello.

Ogni giocata che l'utente decide di registrare viene salvata PRIMA della
partita, con la probabilità del modello e (se nota) la quota. A partita finita
l'esito viene calcolato dal risultato reale. Dopo qualche decina di giocate
si vede se il modello è davvero calibrato e se la strategia avrebbe reso.

Regole per non ingannarsi:
  * una giocata già registrata non si sovrascrive (vale la prima stima, quella
    fatta prima del fischio d'inizio), altrimenti si potrebbe "ritoccare" il
    passato;
  * con pochi risultati le percentuali non dicono nulla: l'app mostra un
    intervallo di confidenza e lo dichiara apertamente;
  * il file è un CSV accanto al codice (come assenze.csv): su servizi che
    azzerano il disco a ogni riavvio va scaricato o spostato su un database.
"""

from __future__ import annotations

import logging
import math
import os
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from config import adesso
from dati import carica_dati_campionato
from resilienza import ERRORE

log = logging.getLogger("b-betting")

FILE_REGISTRO = Path(__file__).parent / "registro_pronostici.csv"
_LOCK = threading.Lock()

COLONNE = [
    "id", "registrato_il", "campionato", "stagione", "data",
    "squadra1", "squadra2", "giocata", "prob_modello", "quota",
    "bookmaker", "fonte", "stato", "risultato", "chiuso_il",
]
# stato: aperto | vinta | persa | non_trovata (partita mai rintracciata)
GIORNI_ATTESA_MAX = 21
CAMPIONE_MINIMO = 30  # sotto questa soglia le percentuali sono solo rumore


# --------------------------------------------------------------------------
# Giocate: codici e valutazione
# --------------------------------------------------------------------------

def codice_giocata(testo):
    """Normalizza la giocata ('1 - Inter' -> '1', 'NoGoal' -> 'NoGoal')."""
    t = str(testo or "").strip()
    if t.startswith("1 - "):
        return "1"
    if t.startswith("2 - "):
        return "2"
    return t


def esito_giocata(codice, gol1, gol2):
    """True/False se la giocata è vinta/persa; None se non riconosciuta."""
    try:
        a, b = int(gol1), int(gol2)
    except (TypeError, ValueError):
        return None
    tot = a + b
    regole = {
        "1": a > b,
        "X": a == b,
        "2": a < b,
        "1X": a >= b,
        "X2": a <= b,
        "12": a != b,
        "Over 1.5": tot > 1.5,
        "Under 1.5": tot < 1.5,
        "Over 2.5": tot > 2.5,
        "Under 2.5": tot < 2.5,
        "Over 3.5": tot > 3.5,
        "Under 3.5": tot < 3.5,
        "Goal": a > 0 and b > 0,
        "NoGoal": a == 0 or b == 0,
    }
    return regole.get(codice)


# --------------------------------------------------------------------------
# File
# --------------------------------------------------------------------------

def _leggi():
    """DataFrame del registro. Non solleva mai: file assente o rovinato -> vuoto
    (un file rovinato viene messo da parte, non cancellato)."""
    if not FILE_REGISTRO.exists():
        return pd.DataFrame(columns=COLONNE)
    try:
        df = pd.read_csv(FILE_REGISTRO, dtype=str, keep_default_na=False)
    except Exception as e:  # noqa: BLE001
        log.exception("Registro illeggibile")
        try:
            copia = FILE_REGISTRO.with_suffix(f".corrotto-{int(datetime.now().timestamp())}.csv")
            os.replace(FILE_REGISTRO, copia)
            st.error(
                f"❌ Il file del registro era illeggibile ({type(e).__name__}). "
                f"L'ho messo da parte come «{copia.name}» e ne parto uno nuovo."
            )
        except OSError:
            st.error("❌ Il file del registro è illeggibile e non riesco a metterlo da parte.")
        return pd.DataFrame(columns=COLONNE)
    return df.reindex(columns=COLONNE, fill_value="")


def _scrivi(df):
    """Scrittura atomica: o c'è il file nuovo completo o resta il vecchio."""
    tmp = FILE_REGISTRO.with_suffix(".tmp")
    df.reindex(columns=COLONNE, fill_value="").to_csv(tmp, index=False)
    os.replace(tmp, FILE_REGISTRO)
    try:  # copia remota (se configurata): un suo errore non deve disturbare il salvataggio locale
        import backup_remoto

        backup_remoto.sincronizza("registro_pronostici.csv")
    except Exception:  # noqa: BLE001
        pass


def _chiave(r):
    return (r["campionato"], r["stagione"], r["data"], r["squadra1"], r["squadra2"], r["giocata"])


# --------------------------------------------------------------------------
# Registrazione
# --------------------------------------------------------------------------

def registra(giocate, fonte):
    """Salva nuove giocate. ``giocate``: lista di dict con campionato, stagione,
    data, squadra1, squadra2, giocata, prob_modello e opzionali quota/bookmaker.

    Ritorna ``(nuove, gia_presenti, scartate)``. Solleva OSError se il disco non
    è scrivibile (il chiamante mostra l'errore)."""
    adesso_s = adesso().strftime("%Y-%m-%d %H:%M")
    with _LOCK:
        df = _leggi()
        presenti = {_chiave(r) for r in df.to_dict("records")}
        nuove, gia, scartate = [], 0, 0
        for g in giocate:
            try:
                riga = {
                    "id": uuid.uuid4().hex[:10],
                    "registrato_il": adesso_s,
                    "campionato": str(g["campionato"]),
                    "stagione": str(g["stagione"]),
                    "data": str(g["data"])[:10],
                    "squadra1": str(g["squadra1"]),
                    "squadra2": str(g["squadra2"]),
                    "giocata": codice_giocata(g["giocata"]),
                    "prob_modello": f"{float(g['prob_modello']):.2f}",
                    "quota": "" if g.get("quota") in (None, "") else f"{float(g['quota']):.2f}",
                    "bookmaker": str(g.get("bookmaker") or ""),
                    "fonte": fonte,
                    "stato": "aperto",
                    "risultato": "",
                    "chiuso_il": "",
                }
                p = float(riga["prob_modello"])
                if not (0 < p <= 100) or not riga["squadra1"] or not riga["squadra2"]:
                    raise ValueError("dati non validi")
                if riga["quota"] and float(riga["quota"]) <= 1.0:
                    riga["quota"] = ""  # una quota <= 1 non è una quota
                if riga["data"] < adesso_s[:10]:
                    # il registro vale solo se si scrive PRIMA della partita:
                    # una partita di ieri è già giocata, il risultato è noto
                    raise ValueError("partita già passata")
            except (KeyError, TypeError, ValueError):
                scartate += 1
                continue
            if _chiave(riga) in presenti:
                gia += 1
                continue
            presenti.add(_chiave(riga))
            nuove.append(riga)
        if nuove:
            _scrivi(pd.concat([df, pd.DataFrame(nuove)], ignore_index=True))
    return len(nuove), gia, scartate


def bottone_registra(chiave, giocate, fonte, etichetta="📌 Registra nel registro pronostici"):
    """Pulsante che registra ``giocate``. Non solleva mai."""
    if not giocate:
        return
    if not st.button(f"{etichetta} ({len(giocate)})", key=chiave):
        return
    try:
        nuove, gia, scartate = registra(giocate, fonte)
    except OSError as e:
        st.error(
            f"❌ Non riesco a scrivere il registro ({e}). Il disco potrebbe essere "
            "in sola lettura: su alcuni servizi online serve un database."
        )
        return
    except Exception as e:  # noqa: BLE001
        log.exception("Registrazione fallita")
        st.error(f"❌ Registrazione non riuscita: {type(e).__name__}.")
        return
    if nuove:
        st.success(
            f"✅ Registrate {nuove} giocate"
            + (f" ({gia} erano già presenti)" if gia else "")
            + ". Le trovi nella pagina «📒 Registro pronostici»."
        )
    elif gia:
        st.info("Queste giocate sono già nel registro: la stima originale resta quella.")
    if scartate:
        st.warning(f"⚠️ {scartate} giocate scartate perché con dati incompleti.")


def da_consigli(consigli, stagione):
    """Converte i consigli di AI Advice. Salta quelli senza squadre separate."""
    out = []
    for c in consigli:
        if not c.get("t1") or not c.get("t2"):
            continue
        out.append({
            "campionato": c["campionato"], "stagione": stagione, "data": c["data"],
            "squadra1": c["t1"], "squadra2": c["t2"], "giocata": c["giocata"],
            "prob_modello": c["p"],
        })
    return out


def da_radar(righe, campionato, stagione):
    """Converte i segnali del Radar (con quota reale)."""
    return [{
        "campionato": campionato, "stagione": stagione, "data": r["Data"],
        "squadra1": r["_t1"], "squadra2": r["_t2"], "giocata": r["Esito"],
        "prob_modello": r["Modello %"], "quota": r["Quota"], "bookmaker": r["Bookmaker"],
    } for r in righe]


# --------------------------------------------------------------------------
# Chiusura degli esiti
# --------------------------------------------------------------------------

def _trova_partita(matches, riga):
    """Partita giocata che corrisponde alla riga (stessa coppia, data vicina)."""
    try:
        d0 = datetime.strptime(riga["data"], "%Y-%m-%d")
    except ValueError:
        return None
    limite = (d0 + timedelta(days=10)).strftime("%Y-%m-%d")
    migliore = None
    for m in matches:
        if m.get("team1") != riga["squadra1"] or m.get("team2") != riga["squadra2"]:
            continue
        data = str(m.get("date", ""))
        if not (riga["data"] <= data <= limite):
            continue
        if migliore is None or data < str(migliore.get("date", "")):
            migliore = m
    return migliore


def chiudi_esiti():
    """Chiude le giocate aperte le cui partite sono state giocate.

    Ritorna ``(chiuse, ancora_aperte, problemi)`` con ``problemi`` = elenco di
    messaggi per l'utente. Non solleva mai per problemi di rete o di dati."""
    problemi = []
    oggi = adesso().strftime("%Y-%m-%d")
    with _LOCK:
        df = _leggi()
        if df.empty:
            return 0, 0, problemi
        aperte = df[(df["stato"] == "aperto") & (df["data"] <= oggi)]
        if aperte.empty:
            return 0, int((df["stato"] == "aperto").sum()), problemi

        chiuse = 0
        cache = {}
        for idx, r in aperte.iterrows():
            k = (r["campionato"], r["stagione"])
            if k not in cache:
                try:
                    d = carica_dati_campionato(*k)
                except Exception as e:  # noqa: BLE001
                    d = {"matches": [], "stato": ERRORE, "messaggio": str(e)}
                cache[k] = d
                if d.get("stato") == ERRORE:
                    problemi.append(
                        f"{k[0]} {k[1]}: dati non scaricabili, le giocate restano aperte."
                    )
            d = cache[k]
            if d.get("stato") == ERRORE:
                continue
            m = _trova_partita(d.get("matches", []), r)
            ft = (m or {}).get("score", {}).get("ft") if m else None
            if ft:
                esito = esito_giocata(r["giocata"], ft[0], ft[1])
                if esito is None:
                    continue
                df.loc[idx, "stato"] = "vinta" if esito else "persa"
                df.loc[idx, "risultato"] = f"{ft[0]}-{ft[1]}"
                df.loc[idx, "chiuso_il"] = oggi
                chiuse += 1
                continue
            try:
                vecchia = (adesso().date() - datetime.strptime(r["data"], "%Y-%m-%d").date()).days
            except ValueError:
                vecchia = 0
            if vecchia > GIORNI_ATTESA_MAX:
                df.loc[idx, "stato"] = "non_trovata"
                df.loc[idx, "chiuso_il"] = oggi
        try:
            _scrivi(df)
        except OSError as e:
            problemi.append(f"Impossibile salvare gli esiti ({e}).")
            return 0, int((df["stato"] == "aperto").sum()), problemi
        return chiuse, int((df["stato"] == "aperto").sum()), problemi


# --------------------------------------------------------------------------
# Statistiche
# --------------------------------------------------------------------------

def intervallo_wilson(vinte, n, z=1.96):
    """Intervallo di confidenza al 95% per una frequenza (in %)."""
    if n <= 0:
        return 0.0, 0.0
    p = vinte / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    mezza = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centro - mezza) * 100, min(1.0, centro + mezza) * 100


def statistiche(df):
    """Indicatori sulle giocate chiuse. Ritorna dict (n=0 se non ce ne sono)."""
    ch = df[df["stato"].isin(["vinta", "persa"])].copy()
    if ch.empty:
        return {"n": 0}
    ch["y"] = (ch["stato"] == "vinta").astype(float)
    ch["p"] = pd.to_numeric(ch["prob_modello"], errors="coerce") / 100
    ch["q"] = pd.to_numeric(ch["quota"], errors="coerce")
    ch = ch.dropna(subset=["p"])
    if ch.empty:
        return {"n": 0}
    n = len(ch)
    vinte = int(ch["y"].sum())
    out = {
        "n": n,
        "vinte": vinte,
        "hit": vinte / n * 100,
        "prob_media": ch["p"].mean() * 100,
        "brier": float(((ch["p"] - ch["y"]) ** 2).mean()),
        "ic": intervallo_wilson(vinte, n),
    }
    # Riferimento: chi prevede sempre la frequenza media ottiene questo Brier
    f = ch["y"].mean()
    out["brier_base"] = float(((f - ch["y"]) ** 2).mean())
    con_q = ch[ch["q"] > 1.0]
    if len(con_q):
        profitto = (con_q["y"] * (con_q["q"] - 1) - (1 - con_q["y"])).sum()
        out["n_quota"] = len(con_q)
        out["roi"] = float(profitto / len(con_q) * 100)
    return out


def tabella_calibrazione(df):
    """Probabilità dichiarata contro frequenza reale, per fasce."""
    ch = df[df["stato"].isin(["vinta", "persa"])].copy()
    if ch.empty:
        return pd.DataFrame()
    ch["p"] = pd.to_numeric(ch["prob_modello"], errors="coerce")
    ch["y"] = (ch["stato"] == "vinta").astype(float)
    ch = ch.dropna(subset=["p"])
    fasce = [0, 40, 50, 60, 70, 101]
    nomi = ["<40%", "40-50%", "50-60%", "60-70%", "≥70%"]
    ch["fascia"] = pd.cut(ch["p"], bins=fasce, labels=nomi, right=False)
    righe = []
    for nome in nomi:
        g = ch[ch["fascia"] == nome]
        if len(g):
            righe.append({
                "Fascia": nome,
                "Giocate": len(g),
                "Prob. dichiarata %": round(g["p"].mean(), 1),
                "Vinte realmente %": round(g["y"].mean() * 100, 1),
            })
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# Pagina
# --------------------------------------------------------------------------

def mostra_registro():
    st.subheader("📒 Registro pronostici")
    st.caption(
        "Qui vedi come vanno davvero le giocate che hai registrato. Si registra "
        "prima della partita (pulsanti 📌 in AI Advice e Radar) e l'esito si "
        "chiude da solo a partita finita. Non è una garanzia di nulla: serve a "
        "capire se il modello merita fiducia. Solo maggiorenni, gioca "
        "responsabilmente."
    )

    with st.spinner("Aggiorno gli esiti delle partite giocate…"):
        try:
            chiuse, aperte, problemi = chiudi_esiti()
        except Exception as e:  # noqa: BLE001
            log.exception("Chiusura esiti fallita")
            st.error(f"❌ Aggiornamento esiti non riuscito: {type(e).__name__}.")
            chiuse, aperte, problemi = 0, 0, []
    for p in problemi:
        st.warning(f"⚠️ {p}")
    if chiuse:
        st.success(f"✅ Chiuse {chiuse} giocate con il risultato reale.")

    df = _leggi()
    if df.empty:
        st.info(
            "Il registro è vuoto. Apri AI Advice o Radar valore e premi "
            "«📌 Registra» per iniziare."
        )
        return

    s = statistiche(df)
    st.caption(f"Giocate registrate: {len(df)} · chiuse: {s['n']} · ancora aperte: {aperte}")

    if s["n"] == 0:
        st.info("Nessuna partita ancora conclusa tra quelle registrate: torna dopo le gare.")
    else:
        c1, c2 = st.columns(2)
        c1.metric("Giocate vinte", f"{s['hit']:.1f}%", f"{s['vinte']} su {s['n']}", delta_color="off")
        c2.metric("Prob. media del modello", f"{s['prob_media']:.1f}%")
        lo, hi = s["ic"]
        st.caption(
            f"Intervallo di confidenza al 95% sulla percentuale reale: {lo:.0f}%–{hi:.0f}%."
        )
        c3, c4 = st.columns(2)
        migliore = s["brier"] < s["brier_base"]
        c3.metric(
            "Errore Brier", f"{s['brier']:.3f}",
            "meglio del riferimento" if migliore else "peggio del riferimento",
            delta_color="normal" if migliore else "inverse",
        )
        if "roi" in s:
            c4.metric("Resa simulata (1 € a giocata)", f"{s['roi']:+.1f}%",
                      f"su {s['n_quota']} con quota", delta_color="off")
        else:
            c4.metric("Resa simulata", "n.d.", "nessuna quota registrata", delta_color="off")

        if s["n"] < CAMPIONE_MINIMO:
            st.warning(
                f"⚠️ Solo {s['n']} giocate chiuse: sotto {CAMPIONE_MINIMO} le percentuali "
                "oscillano molto per pura fortuna. Non trarre conclusioni, né positive "
                "né negative."
            )
        else:
            diff = s["hit"] - s["prob_media"]
            if abs(diff) <= 5:
                st.info("Il modello è in linea con la realtà: vincite vicine alle probabilità dichiarate.")
            elif diff < 0:
                st.warning(
                    f"Il modello è ottimista: dichiara {s['prob_media']:.0f}% ma vince "
                    f"il {s['hit']:.0f}%. Pesa meno le sue probabilità."
                )
            else:
                st.info("Il modello è prudente: vince più di quanto dichiara.")

        cal = tabella_calibrazione(df)
        if not cal.empty:
            st.markdown("**Calibrazione**")
            st.dataframe(cal, use_container_width=True, hide_index=True)
            st.caption(
                "Se il modello è onesto, le due colonne sono simili. Le fasce con "
                "poche giocate (colonna «Giocate») non vanno prese sul serio."
            )

    with st.expander(f"Elenco giocate ({len(df)})"):
        vista = df.sort_values("data", ascending=False)[
            ["data", "squadra1", "squadra2", "giocata", "prob_modello", "quota",
             "fonte", "stato", "risultato"]
        ]
        st.dataframe(vista, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Scarica il registro (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="registro_pronostici.csv",
        mime="text/csv",
        key="registro_download",
    )
    st.caption(
        "Fai ogni tanto una copia: se l'app gira su un servizio che azzera il disco "
        "a ogni riavvio, il registro si perde."
    )
