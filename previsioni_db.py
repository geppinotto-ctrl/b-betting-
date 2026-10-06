"""Archivio delle previsioni per il test prospettico (nessuna dipendenza da Streamlit).

Cosa garantisce:
  * le previsioni sono IMMUTABILI: due trigger del database rifiutano ogni
    UPDATE e DELETE su ``previsioni``, ``batches`` ed ``esclusioni``. È una
    protezione contro i bug del programma, non contro chi apre il file con
    uno strumento esterno;
  * un risultato già liquidato non si cambia: un valore diverso arrivato dopo
    finisce in ``risultati_conflitti`` e va deciso a mano;
  * la registrazione di un batch è una transazione unica: o c'è tutto o non
    c'è niente;
  * ripetere lo stesso batch con lo stesso contenuto non crea duplicati
    (impronta del contenuto);
  * scritture concorrenti: ``BEGIN IMMEDIATE`` + attesa di 15 s, quindi due
    sessioni aperte insieme non si sovrascrivono (una aspetta l'altra);
  * le probabilità sono salvate in [0, 1]; la conversione dalle percentuali
    dell'app avviene una volta sola, al confine (``previsioni_batch``).

Regola della coorte primaria: per ogni (partita, motore, configurazione) vale
la PRIMA previsione valida registrata. Le successive restano archivio e non
cambiano il punteggio.
"""

import hashlib
import io
import json
import math
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import persistenza

NOME_DB = "previsioni.db"
SCHEMA_VERSIONE = 1
EPS = 1e-15  # taglio per il log-loss: log(0) non esiste, si usa log(EPS)

TABELLE = ("batches", "previsioni", "esclusioni", "risultati", "risultati_conflitti")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(
    chiave TEXT PRIMARY KEY,
    valore TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS batches(
    batch_id TEXT PRIMARY KEY,
    creato_il_utc TEXT NOT NULL,
    campionato TEXT NOT NULL,
    stagione TEXT NOT NULL,
    da_data TEXT NOT NULL,
    a_data TEXT NOT NULL,
    versione_app TEXT NOT NULL,
    stato_dati TEXT NOT NULL,
    cutoff_dati TEXT,
    n_eleggibili INTEGER NOT NULL,
    n_escluse INTEGER NOT NULL,
    n_previsioni INTEGER NOT NULL,
    note TEXT
);
CREATE TABLE IF NOT EXISTS esclusioni(
    batch_id TEXT NOT NULL,
    match_key TEXT NOT NULL,
    descrizione TEXT NOT NULL,
    motivo TEXT NOT NULL,
    PRIMARY KEY (batch_id, match_key)
);
CREATE TABLE IF NOT EXISTS previsioni(
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL REFERENCES batches(batch_id),
    match_key TEXT NOT NULL,
    campionato TEXT NOT NULL,
    stagione TEXT NOT NULL,
    data_partita TEXT NOT NULL,
    ora_kickoff TEXT,
    squadra_casa TEXT NOT NULL,
    squadra_ospite TEXT NOT NULL,
    creato_il_utc TEXT NOT NULL,
    motore TEXT NOT NULL,
    versione_motore TEXT NOT NULL,
    config_id TEXT NOT NULL,
    parametri TEXT NOT NULL,
    n_storico INTEGER,
    n_storico_casa INTEGER,
    n_storico_ospite INTEGER,
    cutoff_dati TEXT,
    stato_dati TEXT,
    stato TEXT NOT NULL CHECK (stato IN ('ok', 'fallita', 'invalida')),
    nota TEXT,
    l1 REAL, l2 REAL,
    p1 REAL, px REAL, p2 REAL, p_over25 REAL, p_goal REAL,
    b1 REAL, bx REAL, b2 REAL, b_over25 REAL, b_goal REAL,
    impronta TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_prev_match ON previsioni(match_key, motore, config_id);
CREATE INDEX IF NOT EXISTS idx_prev_camp ON previsioni(campionato, stagione);
CREATE TABLE IF NOT EXISTS risultati(
    match_key TEXT PRIMARY KEY,
    stato TEXT NOT NULL CHECK (stato IN ('liquidata', 'ambigua', 'rinviata')),
    gol_casa INTEGER,
    gol_ospite INTEGER,
    data_osservata TEXT,
    fonte TEXT NOT NULL,
    acquisito_il_utc TEXT NOT NULL,
    nota TEXT
);
CREATE TABLE IF NOT EXISTS risultati_conflitti(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_key TEXT NOT NULL,
    rilevato_il_utc TEXT NOT NULL,
    gol_casa INTEGER,
    gol_ospite INTEGER,
    nota TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_conflitti ON risultati_conflitti(match_key, gol_casa, gol_ospite);

CREATE TRIGGER IF NOT EXISTS previsioni_no_update BEFORE UPDATE ON previsioni
BEGIN SELECT RAISE(ABORT, 'le previsioni sono immutabili'); END;
CREATE TRIGGER IF NOT EXISTS previsioni_no_delete BEFORE DELETE ON previsioni
BEGIN SELECT RAISE(ABORT, 'le previsioni sono immutabili'); END;
CREATE TRIGGER IF NOT EXISTS batches_no_update BEFORE UPDATE ON batches
BEGIN SELECT RAISE(ABORT, 'i batch sono immutabili'); END;
CREATE TRIGGER IF NOT EXISTS batches_no_delete BEFORE DELETE ON batches
BEGIN SELECT RAISE(ABORT, 'i batch sono immutabili'); END;
CREATE TRIGGER IF NOT EXISTS esclusioni_no_update BEFORE UPDATE ON esclusioni
BEGIN SELECT RAISE(ABORT, 'le esclusioni sono immutabili'); END;
CREATE TRIGGER IF NOT EXISTS esclusioni_no_delete BEFORE DELETE ON esclusioni
BEGIN SELECT RAISE(ABORT, 'le esclusioni sono immutabili'); END;
CREATE TRIGGER IF NOT EXISTS risultati_liquidata_no_update BEFORE UPDATE ON risultati
WHEN OLD.stato = 'liquidata'
BEGIN SELECT RAISE(ABORT, 'un risultato liquidato non si modifica: usa i conflitti'); END;
CREATE TRIGGER IF NOT EXISTS risultati_no_delete BEFORE DELETE ON risultati
BEGIN SELECT RAISE(ABORT, 'i risultati non si cancellano'); END;
"""


# ------------------------------------------------------------------
# Connessione
# ------------------------------------------------------------------


NOME_DB_PROVA = "previsioni_prova.db"


def percorso_db(prova=False):
    """``prova=True``: archivio separato per fare le prove senza sporcare quello vero."""
    return persistenza.cartella() / (NOME_DB_PROVA if prova else NOME_DB)


def ora_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def _con(db=None, scrittura=False):
    """Connessione con commit/rollback. ``scrittura=True`` prende il lock subito."""
    db = Path(db) if db else percorso_db()
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db), timeout=15, isolation_level=None)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(_SCHEMA)
        con.execute(
            "INSERT OR IGNORE INTO meta(chiave, valore) VALUES ('schema_versione', ?)",
            (str(SCHEMA_VERSIONE),),
        )
        if scrittura:
            con.execute("BEGIN IMMEDIATE")
        try:
            yield con
            if scrittura:
                con.execute("COMMIT")
        except BaseException:
            if scrittura:
                try:
                    con.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
            raise
    finally:
        con.close()


# ------------------------------------------------------------------
# Validazione e impronta
# ------------------------------------------------------------------

CAMPI_PROB = ("p1", "px", "p2", "p_over25", "p_goal")


def valida_probabilita(rec, tolleranza=1e-6):
    """('ok', '') oppure ('invalida', motivo). Non corregge mai nulla."""
    for k in CAMPI_PROB + ("l1", "l2"):
        v = rec.get(k)
        if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
            return "invalida", f"{k} mancante o non numerico"
        if not math.isfinite(v):
            return "invalida", f"{k} non finito"
    for k in CAMPI_PROB:
        if not 0.0 <= rec[k] <= 1.0:
            return "invalida", f"{k} fuori da [0, 1] ({rec[k]})"
    somma = rec["p1"] + rec["px"] + rec["p2"]
    if abs(somma - 1.0) > tolleranza:
        return "invalida", f"1X2 non somma a 1 ({somma:.6f})"
    if rec["l1"] < 0 or rec["l2"] < 0:
        return "invalida", "gol attesi negativi"
    return "ok", ""


def _impronta(rec, stato):
    base = {
        "k": rec["match_key"], "m": rec["motore"], "c": rec["config_id"], "v": rec.get("versione_motore"),
        "n": rec.get("n_storico"), "cut": rec.get("cutoff_dati"), "s": stato,
        "e": rec.get("errore") if stato != "ok" else None,
    }
    if stato == "ok":
        for k in CAMPI_PROB + ("l1", "l2"):
            base[k] = round(rec[k], 9)
    return hashlib.sha256(json.dumps(base, sort_keys=True).encode()).hexdigest()


def _num(rec, k):
    v = rec.get(k)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


# ------------------------------------------------------------------
# Registrazione
# ------------------------------------------------------------------


def registra_batch(db, meta, record, esclusioni=(), ora=None):
    """Registra un batch in una sola transazione.

    ``meta``: campionato, stagione, da_data, a_data, versione_app, stato_dati,
    cutoff_dati, n_eleggibili. ``record``: una riga per (partita, motore).
    Una riga con ``errore`` viene conservata come 'fallita' (mai nascosta);
    una che non supera la validazione come 'invalida' (mai "aggiustata").

    Ritorna ``{"batch_id", "nuove", "duplicate", "fallite", "invalide"}``.
    ``batch_id`` è None se tutto il contenuto era già registrato.
    """
    ora = ora or ora_utc()
    esclusioni = list(esclusioni)
    with _con(db, scrittura=True) as con:
        nuove = []
        viste = set()
        duplicate = 0
        for rec in record:
            if rec.get("errore"):
                stato, nota = "fallita", str(rec["errore"])[:300]
            else:
                stato, nota = valida_probabilita(rec)
            imp = _impronta(rec, stato if stato != "ok" else "ok")
            if imp in viste or con.execute(
                "SELECT 1 FROM previsioni WHERE impronta = ?", (imp,)
            ).fetchone():
                duplicate += 1
                continue
            viste.add(imp)
            nuove.append((rec, stato, nota, imp))
        if not nuove:
            return {"batch_id": None, "nuove": 0, "duplicate": duplicate, "fallite": 0, "invalide": 0}

        batch_id = f"B{ora[:19].replace('-', '').replace(':', '').replace('T', '-')}-{hashlib.sha1(os.urandom(8)).hexdigest()[:4]}"
        con.execute(
            """INSERT INTO batches(batch_id, creato_il_utc, campionato, stagione, da_data, a_data,
               versione_app, stato_dati, cutoff_dati, n_eleggibili, n_escluse, n_previsioni, note)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (batch_id, ora, meta["campionato"], meta["stagione"], meta["da_data"], meta["a_data"],
             meta["versione_app"], meta.get("stato_dati", "ok"), meta.get("cutoff_dati"),
             int(meta.get("n_eleggibili", 0)), len(esclusioni), len(nuove), meta.get("note")),
        )
        for e in esclusioni:
            con.execute(
                "INSERT OR IGNORE INTO esclusioni(batch_id, match_key, descrizione, motivo) VALUES (?,?,?,?)",
                (batch_id, e["match_key"], e["descrizione"], e["motivo"]),
            )
        for rec, stato, nota, imp in nuove:
            con.execute(
                """INSERT INTO previsioni(batch_id, match_key, campionato, stagione, data_partita,
                   ora_kickoff, squadra_casa, squadra_ospite, creato_il_utc, motore, versione_motore,
                   config_id, parametri, n_storico, n_storico_casa, n_storico_ospite, cutoff_dati,
                   stato_dati, stato, nota, l1, l2, p1, px, p2, p_over25, p_goal,
                   b1, bx, b2, b_over25, b_goal, impronta)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (batch_id, rec["match_key"], rec["campionato"], rec["stagione"], rec["data_partita"],
                 rec.get("ora_kickoff") or None, rec["squadra_casa"], rec["squadra_ospite"], ora,
                 rec["motore"], rec["versione_motore"], rec["config_id"],
                 json.dumps(rec.get("parametri", {}), sort_keys=True),
                 rec.get("n_storico"), rec.get("n_storico_casa"), rec.get("n_storico_ospite"),
                 rec.get("cutoff_dati"), rec.get("stato_dati"), stato, nota or None,
                 _num(rec, "l1") if stato == "ok" else None, _num(rec, "l2") if stato == "ok" else None,
                 *[(_num(rec, k) if stato == "ok" else None) for k in CAMPI_PROB],
                 *[_num(rec, k) for k in ("b1", "bx", "b2", "b_over25", "b_goal")],
                 imp),
            )
        return {
            "batch_id": batch_id,
            "nuove": len(nuove),
            "duplicate": duplicate,
            "fallite": sum(1 for n in nuove if n[1] == "fallita"),
            "invalide": sum(1 for n in nuove if n[1] == "invalida"),
        }


# ------------------------------------------------------------------
# Liquidazione dei risultati
# ------------------------------------------------------------------


def _giorni(a, b):
    try:
        return (datetime.strptime(a[:10], "%Y-%m-%d") - datetime.strptime(b[:10], "%Y-%m-%d")).days
    except (ValueError, TypeError):
        return None


FINESTRA_ABBINAMENTO = 10  # giorni di tolleranza tra la data prevista e quella osservata


def abbina(partita, matches):
    """Cerca nei dati la partita di una previsione.

    ``partita``: dict con data_partita, squadra_casa, squadra_ospite.
    Ritorna ``(esito, match, nota)`` con esito in:
    ``liquidata`` (trovata e finita), ``rinviata`` (trovata con data diversa e non
    ancora giocata), ``ambigua`` (più candidati), ``attesa`` (non ancora).
    Non assegna MAI un risultato per somiglianza: servono le stesse squadre
    (stesso campo) e una sola candidata nella finestra di date.
    """
    cand = [
        m for m in matches
        if isinstance(m, dict)
        and m.get("team1") == partita["squadra_casa"] and m.get("team2") == partita["squadra_ospite"]
    ]
    if not cand:
        return "attesa", None, ""
    vicine = [
        m for m in cand
        if (_giorni(str(m.get("date", "")), partita["data_partita"]) is not None
            and abs(_giorni(str(m.get("date", "")), partita["data_partita"])) <= FINESTRA_ABBINAMENTO)
    ]
    if len(vicine) > 1:
        return "ambigua", None, f"{len(vicine)} partite con le stesse squadre vicine alla data"
    if not vicine:
        return "attesa", None, ""
    m = vicine[0]
    ft = (m.get("score") or {}).get("ft") if isinstance(m.get("score"), dict) else None
    data_oss = str(m.get("date", ""))[:10]
    diversa = data_oss != partita["data_partita"][:10]
    if ft and isinstance(ft, (list, tuple)) and len(ft) == 2:
        nota = f"data osservata {data_oss}, prevista {partita['data_partita']}" if diversa else ""
        return "liquidata", m, nota
    if diversa and (_giorni(data_oss, partita["data_partita"]) or 0) > 0:
        return "rinviata", m, f"riprogrammata al {data_oss}"
    return "attesa", None, ""


def liquida(db, campionato, stagione, matches, fonte="dati", ora=None):
    """Aggiorna lo stato dei risultati per le previsioni di un campionato/stagione.

    Non tocca mai le previsioni. Ritorna i conteggi.
    """
    ora = ora or ora_utc()
    out = {"liquidate": 0, "ambigue": 0, "rinviate": 0, "conflitti": 0, "in_attesa": 0}
    with _con(db, scrittura=True) as con:
        righe = con.execute(
            """SELECT DISTINCT match_key, data_partita, squadra_casa, squadra_ospite
               FROM previsioni WHERE campionato = ? AND stagione = ?""",
            (campionato, stagione),
        ).fetchall()
        for r in righe:
            esito, m, nota = abbina(dict(r), matches)
            attuale = con.execute("SELECT * FROM risultati WHERE match_key = ?", (r["match_key"],)).fetchone()
            if esito == "attesa":
                if not attuale:
                    out["in_attesa"] += 1
                continue
            if esito == "liquidata":
                ft = m["score"]["ft"]
                gc, go = int(ft[0]), int(ft[1])
                if attuale and attuale["stato"] == "liquidata":
                    if (attuale["gol_casa"], attuale["gol_ospite"]) != (gc, go):
                        cur = con.execute(
                            """INSERT OR IGNORE INTO risultati_conflitti(match_key, rilevato_il_utc, gol_casa, gol_ospite, nota)
                               VALUES (?,?,?,?,?)""",
                            (r["match_key"], ora, gc, go, "risultato diverso da quello già liquidato"),
                        )
                        out["conflitti"] += cur.rowcount
                    continue
                if attuale:
                    con.execute(
                        """UPDATE risultati SET stato='liquidata', gol_casa=?, gol_ospite=?, data_osservata=?,
                           fonte=?, acquisito_il_utc=?, nota=? WHERE match_key=?""",
                        (gc, go, str(m.get("date", ""))[:10], fonte, ora, nota or None, r["match_key"]),
                    )
                else:
                    con.execute(
                        """INSERT INTO risultati(match_key, stato, gol_casa, gol_ospite, data_osservata, fonte, acquisito_il_utc, nota)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (r["match_key"], "liquidata", gc, go, str(m.get("date", ""))[:10], fonte, ora, nota or None),
                    )
                out["liquidate"] += 1
                continue
            # ambigua / rinviata: si registra lo stato, senza inventare un risultato
            dat = str(m.get("date", ""))[:10] if m else None
            if attuale:
                if attuale["stato"] != "liquidata" and (attuale["stato"], attuale["data_osservata"]) != (esito, dat):
                    con.execute(
                        "UPDATE risultati SET stato=?, data_osservata=?, acquisito_il_utc=?, nota=? WHERE match_key=?",
                        (esito, dat, ora, nota or None, r["match_key"]),
                    )
            else:
                con.execute(
                    """INSERT INTO risultati(match_key, stato, gol_casa, gol_ospite, data_osservata, fonte, acquisito_il_utc, nota)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (r["match_key"], esito, None, None, dat, fonte, ora, nota or None),
                )
            out["ambigue" if esito == "ambigua" else "rinviate"] += 1
    return out


def coppie_da_liquidare(db):
    """Elenco (campionato, stagione) con previsioni non ancora liquidate."""
    with _con(db) as con:
        return [
            (r["campionato"], r["stagione"])
            for r in con.execute(
                """SELECT DISTINCT p.campionato, p.stagione FROM previsioni p
                   LEFT JOIN risultati r ON r.match_key = p.match_key
                   WHERE r.match_key IS NULL OR r.stato != 'liquidata'"""
            )
        ]


# ------------------------------------------------------------------
# Valutazione (formule pure)
# ------------------------------------------------------------------


def brier_1x2(p, reale):
    """Brier multicategoria: somma dei tre scarti al quadrato (0 = perfetto, 2 = peggio).
    ``reale``: 0 = casa, 1 = pareggio, 2 = trasferta. NON è diviso per 3."""
    return sum((p[k] - (1.0 if k == reale else 0.0)) ** 2 for k in range(3))


def logloss_1x2(p, reale):
    return -math.log(max(p[reale], EPS))


def brier_bin(p, y):
    return (p - y) ** 2


def logloss_bin(p, y):
    q = p if y == 1 else 1 - p
    return -math.log(max(q, EPS))


def _reale(gc, go):
    return 0 if gc > go else (1 if gc == go else 2)


def _media_ci(valori):
    n = len(valori)
    if n == 0:
        return None
    m = sum(valori) / n
    if n < 2:
        return {"media": m, "lo": None, "hi": None, "n": n}
    var = sum((v - m) ** 2 for v in valori) / (n - 1)
    se = math.sqrt(var / n)
    return {"media": m, "lo": m - 1.96 * se, "hi": m + 1.96 * se, "n": n}


FASCE = (0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0000001)


def _calibrazione(coppie):
    """coppie: [(p, y)] -> righe per fascia con numerosità."""
    righe = []
    for lo, hi in zip(FASCE[:-1], FASCE[1:]):
        d = [(p, y) for p, y in coppie if lo <= p < hi]
        if d:
            righe.append({
                "da": lo, "a": min(hi, 1.0), "n": len(d),
                "prob_media": sum(p for p, _ in d) / len(d),
                "freq_reale": sum(y for _, y in d) / len(d),
            })
    return righe


def _metriche(righe):
    """righe: dict con p=(p1,px,p2), po, pg, reale, over, goal, b=(..), bo, bg."""
    n = len(righe)
    if n == 0:
        return None
    out = {"n": n}
    mod = {
        "brier": sum(brier_1x2(r["p"], r["reale"]) for r in righe) / n,
        "logloss": sum(logloss_1x2(r["p"], r["reale"]) for r in righe) / n,
        "acc": sum(1 for r in righe if max(range(3), key=lambda k: r["p"][k]) == r["reale"]) / n,
        "brier_over": sum(brier_bin(r["po"], r["over"]) for r in righe) / n,
        "logloss_over": sum(logloss_bin(r["po"], r["over"]) for r in righe) / n,
        "brier_goal": sum(brier_bin(r["pg"], r["goal"]) for r in righe) / n,
        "logloss_goal": sum(logloss_bin(r["pg"], r["goal"]) for r in righe) / n,
    }
    con_b = [r for r in righe if r["b"] is not None]
    rif = None
    if con_b:
        nb = len(con_b)
        rif = {
            "n": nb,
            "brier": sum(brier_1x2(r["b"], r["reale"]) for r in con_b) / nb,
            "logloss": sum(logloss_1x2(r["b"], r["reale"]) for r in con_b) / nb,
        }
        con_bo = [r for r in con_b if r["bo"] is not None and r["bg"] is not None]
        if con_bo:
            rif["brier_over"] = sum(brier_bin(r["bo"], r["over"]) for r in con_bo) / len(con_bo)
            rif["brier_goal"] = sum(brier_bin(r["bg"], r["goal"]) for r in con_bo) / len(con_bo)
    out["modello"], out["riferimento"] = mod, rif
    out["calibrazione_1x2"] = _calibrazione(
        [(r["p"][k], 1.0 if r["reale"] == k else 0.0) for r in righe for k in range(3)]
    )
    out["calibrazione_over"] = _calibrazione([(r["po"], float(r["over"])) for r in righe])
    out["calibrazione_goal"] = _calibrazione([(r["pg"], float(r["goal"])) for r in righe])
    return out


def _carica_primarie(con, campionato=None, solo_dati_ok=False, min_storico=0, da_data=None, a_data=None):
    """Previsioni primarie (prima valida per partita/motore/config)."""
    filtri, par = ["p.stato = 'ok'"], []
    if campionato:
        filtri.append("p.campionato = ?"); par.append(campionato)
    if da_data:
        filtri.append("p.data_partita >= ?"); par.append(da_data)
    if a_data:
        filtri.append("p.data_partita <= ?"); par.append(a_data)
    if solo_dati_ok:
        filtri.append("p.stato_dati = 'ok'")
    if min_storico:
        filtri.append("COALESCE(p.n_storico_casa, 0) >= ? AND COALESCE(p.n_storico_ospite, 0) >= ?")
        par += [min_storico, min_storico]
    sql = f"""
        SELECT p.* FROM previsioni p
        WHERE {' AND '.join(filtri)}
          AND p.prediction_id = (
              SELECT q.prediction_id FROM previsioni q
              WHERE q.match_key = p.match_key AND q.motore = p.motore AND q.config_id = p.config_id
                AND q.stato = 'ok'
              ORDER BY q.creato_il_utc, q.prediction_id LIMIT 1)
    """
    return [dict(r) for r in con.execute(sql, par)]


def valuta(db, campionato=None, solo_dati_ok=False, min_storico=0, da_data=None, a_data=None):
    """Metriche della coorte primaria.

    * ``copertura``: quante previsioni, quante liquidate, in attesa, ambigue, escluse;
    * ``serie``: per (motore, config) metriche sulle partite liquidate di QUELLA serie;
    * ``confronto``: Poisson contro Dixon–Coles sulla coorte COMUNE (stesse partite,
      stessa configurazione), con differenze accoppiate e intervallo di confidenza.
      Differenza negativa = Dixon–Coles meglio (errore più basso).
    """
    with _con(db) as con:
        prim = _carica_primarie(con, campionato, solo_dati_ok, min_storico, da_data, a_data)
        ris = {r["match_key"]: dict(r) for r in con.execute("SELECT * FROM risultati")}
        n_escl = con.execute("SELECT COUNT(*) FROM esclusioni").fetchone()[0]
        n_fall = con.execute("SELECT COUNT(*) FROM previsioni WHERE stato != 'ok'").fetchone()[0]
        n_batch = con.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
    partite = {p["match_key"] for p in prim}
    stati = {"liquidata": 0, "ambigua": 0, "rinviata": 0, "attesa": 0}
    for k in partite:
        stati[ris[k]["stato"] if k in ris else "attesa"] += 1
    copertura = {
        "batch": n_batch, "partite_registrate": len(partite), "liquidate": stati["liquidata"],
        "in_attesa": stati["attesa"], "ambigue": stati["ambigua"], "rinviate": stati["rinviata"],
        "escluse": n_escl, "previsioni_fallite_o_invalide": n_fall,
    }

    def riga(p):
        r = ris[p["match_key"]]
        return {
            "match_key": p["match_key"], "data": p["data_partita"],
            "p": (p["p1"], p["px"], p["p2"]), "po": p["p_over25"], "pg": p["p_goal"],
            "reale": _reale(r["gol_casa"], r["gol_ospite"]),
            "over": 1 if r["gol_casa"] + r["gol_ospite"] > 2 else 0,
            "goal": 1 if r["gol_casa"] > 0 and r["gol_ospite"] > 0 else 0,
            "b": (p["b1"], p["bx"], p["b2"]) if None not in (p["b1"], p["bx"], p["b2"]) else None,
            "bo": p["b_over25"], "bg": p["b_goal"],
        }

    per_serie = {}
    for p in prim:
        if p["match_key"] in ris and ris[p["match_key"]]["stato"] == "liquidata":
            per_serie.setdefault((p["motore"], p["config_id"]), {})[p["match_key"]] = (p, riga(p))
    serie = {}
    for chiave, d in per_serie.items():
        m = _metriche([x[1] for x in d.values()])
        m["periodo"] = (min(x[1]["data"] for x in d.values()), max(x[1]["data"] for x in d.values()))
        serie[chiave] = m

    confronto = None
    configs = {c for (_, c) in per_serie}
    for c in sorted(configs):
        a, b = per_serie.get(("poisson", c), {}), per_serie.get(("dixon_coles", c), {})
        comuni = sorted(set(a) & set(b))
        if not comuni:
            continue
        d_brier = [brier_1x2(b[k][1]["p"], b[k][1]["reale"]) - brier_1x2(a[k][1]["p"], a[k][1]["reale"]) for k in comuni]
        d_ll = [logloss_1x2(b[k][1]["p"], b[k][1]["reale"]) - logloss_1x2(a[k][1]["p"], a[k][1]["reale"]) for k in comuni]
        confronto = {
            "config": c, "n": len(comuni),
            "poisson": _metriche([a[k][1] for k in comuni]),
            "dixon_coles": _metriche([b[k][1] for k in comuni]),
            "delta_brier": _media_ci(d_brier), "delta_logloss": _media_ci(d_ll),
        }
    return {"copertura": copertura, "serie": serie, "confronto": confronto}


def ece(righe_calibrazione):
    """Errore di calibrazione atteso sulle fasce fisse: media pesata di |prob. media - frequenza reale|.

    Con pochi dati è soprattutto rumore: va letto insieme alla numerosità.
    """
    tot = sum(r["n"] for r in righe_calibrazione)
    if not tot:
        return None
    return sum(r["n"] * abs(r["prob_media"] - r["freq_reale"]) for r in righe_calibrazione) / tot


def monitoraggio(db, oggi, campionato=None, finestre=(30, 90)):
    """Salute dell'archivio e delle previsioni alla data ``oggi`` ('YYYY-MM-DD').

    * ``finestre``: Brier, log-loss, ECE e numerosità sulle partite degli ultimi N
      giorni, per ogni motore (nessuna conclusione se il campione è piccolo);
    * ``segnali``: cose da guardare (nessun batch recente, previsioni senza risultato
      da troppo tempo, previsioni fallite o non valide, conflitti, abbinamenti
      ambigui, dati non aggiornati, backup vecchio).
    """
    out = {"finestre": {}, "segnali": []}
    for g in finestre:
        da = (datetime.strptime(oggi, "%Y-%m-%d") - timedelta(days=g)).strftime("%Y-%m-%d")
        v = valuta(db, campionato=campionato, da_data=da, a_data=oggi)
        righe = {}
        for (motore, _cfg), m in v["serie"].items():
            righe[motore] = {
                "n": m["n"], "brier": m["modello"]["brier"], "logloss": m["modello"]["logloss"],
                "ece": ece(m["calibrazione_1x2"]),
                "brier_rif": m["riferimento"]["brier"] if m["riferimento"] else None,
            }
        out["finestre"][g] = righe

    with _con(db) as con:
        def uno(sql, par=()):
            return con.execute(sql, par).fetchone()[0]

        ultimo_batch = uno("SELECT MAX(creato_il_utc) FROM batches")
        n_fall = uno("SELECT COUNT(*) FROM previsioni WHERE stato = 'fallita'")
        n_inv = uno("SELECT COUNT(*) FROM previsioni WHERE stato = 'invalida'")
        n_conf = uno("SELECT COUNT(*) FROM risultati_conflitti")
        n_amb = uno("SELECT COUNT(*) FROM risultati WHERE stato = 'ambigua'")
        n_rinv = uno("SELECT COUNT(*) FROM risultati WHERE stato = 'rinviata'")
        vecchie = uno(
            """SELECT COUNT(DISTINCT p.match_key) FROM previsioni p
               LEFT JOIN risultati r ON r.match_key = p.match_key
               WHERE p.data_partita < ? AND (r.match_key IS NULL OR r.stato != 'liquidata')""",
            ((datetime.strptime(oggi, "%Y-%m-%d") - timedelta(days=3)).strftime("%Y-%m-%d"),),
        )
        non_ok = uno("SELECT COUNT(*) FROM batches WHERE stato_dati != 'ok'")
        ub = con.execute("SELECT valore FROM meta WHERE chiave = 'ultimo_backup_utc'").fetchone()
        n_prev = uno("SELECT COUNT(*) FROM previsioni")
    sig = out["segnali"]
    if n_prev == 0:
        sig.append(("info", "Nessuna previsione registrata: il test non è ancora iniziato."))
    if ultimo_batch:
        gg = (datetime.strptime(oggi, "%Y-%m-%d") - datetime.strptime(ultimo_batch[:10], "%Y-%m-%d")).days
        if gg > 7:
            sig.append(("avviso", f"Ultimo batch di {gg} giorni fa: le partite di questa settimana non sono registrate."))
    if vecchie:
        sig.append(("avviso", f"{vecchie} partite registrate senza risultato da più di 3 giorni: controlla rinvii o nomi squadra."))
    if n_fall or n_inv:
        sig.append(("errore", f"{n_fall} previsioni fallite e {n_inv} non valide: non entrano nella valutazione."))
    if n_conf:
        sig.append(("errore", f"{n_conf} risultati in conflitto con quello già liquidato: serve una decisione manuale."))
    if n_amb:
        sig.append(("avviso", f"{n_amb} partite con abbinamento ambiguo: non sono state liquidate."))
    if n_rinv:
        sig.append(("info", f"{n_rinv} partite riprogrammate, in attesa di essere giocate."))
    if non_ok:
        sig.append(("avviso", f"{non_ok} batch registrati con dati non aggiornati: valutali separatamente."))
    if n_prev:
        if not ub:
            sig.append(("avviso", "Nessun backup scaricato: se il disco si azzera perdi tutto."))
        else:
            gb = (datetime.strptime(oggi, "%Y-%m-%d") - datetime.strptime(ub["valore"][:10], "%Y-%m-%d")).days
            if gb > 7:
                sig.append(("avviso", f"Ultimo backup di {gb} giorni fa."))
    return out


# ------------------------------------------------------------------
# Elenchi
# ------------------------------------------------------------------


def elenco_partite(db, campionato=None, limite=200):
    """Una riga per partita con le probabilità dei due motori (coorte primaria) e lo stato del risultato."""
    with _con(db) as con:
        prim = _carica_primarie(con, campionato)
        ris = {r["match_key"]: dict(r) for r in con.execute("SELECT * FROM risultati")}
        batch_per = {}
        for r in con.execute("SELECT match_key, MIN(batch_id) b FROM previsioni GROUP BY match_key"):
            batch_per[r["match_key"]] = r["b"]
    righe = {}
    for p in prim:
        r = righe.setdefault(p["match_key"], {
            "match_key": p["match_key"], "data": p["data_partita"], "ora": p["ora_kickoff"] or "",
            "campionato": p["campionato"], "casa": p["squadra_casa"], "ospite": p["squadra_ospite"],
            "batch": batch_per.get(p["match_key"], ""),
        })
        sfx = "P" if p["motore"] == "poisson" else "DC"
        r[f"1 {sfx}"], r[f"X {sfx}"], r[f"2 {sfx}"] = p["p1"], p["px"], p["p2"]
    for k, r in righe.items():
        x = ris.get(k)
        r["stato"] = (x["stato"] if x else "in attesa")
        r["risultato"] = f"{x['gol_casa']}-{x['gol_ospite']}" if x and x["stato"] == "liquidata" else ""
    out = sorted(righe.values(), key=lambda r: (r["data"], r["casa"]))
    return out[-limite:]


def esclusioni_recenti(db, batch_id=None, limite=300):
    with _con(db) as con:
        if batch_id is None:
            r = con.execute("SELECT batch_id FROM batches ORDER BY creato_il_utc DESC, batch_id DESC LIMIT 1").fetchone()
            if not r:
                return []
            batch_id = r["batch_id"]
        return [dict(x) for x in con.execute(
            "SELECT * FROM esclusioni WHERE batch_id = ? LIMIT ?", (batch_id, limite))]


# ------------------------------------------------------------------
# Informazioni, backup, ripristino
# ------------------------------------------------------------------


def ambiente():
    """('tipo', 'avviso'): dove sta girando l'app e se il disco è affidabile."""
    if os.environ.get("B_BETTING_DATI", "").strip():
        return "cartella_personalizzata", "I dati stanno nella cartella indicata da B_BETTING_DATI."
    qui = str(Path(__file__).resolve())
    if qui.startswith("/mount/src") or os.environ.get("STREAMLIT_SHARING_MODE"):
        return "streamlit_cloud", (
            "Sembra Streamlit Community Cloud: lì il disco si azzera quando l'app si riavvia "
            "o viene ridistribuita. Scarica il backup dopo OGNI batch."
        )
    if os.environ.get("CODESPACES") == "true":
        return "codespaces", (
            "Sembra GitHub Codespaces: i file restano finché il codespace esiste, ma non è "
            "un archivio garantito. Scarica comunque il backup dopo ogni batch."
        )
    return "locale", "I dati stanno sul disco di questo computer. Fai comunque una copia fuori dal computer."


def info_archivio(db=None):
    db = Path(db) if db else percorso_db()
    with _con(db) as con:
        conta = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABELLE}
        ub = con.execute("SELECT valore FROM meta WHERE chiave = 'ultimo_backup_utc'").fetchone()
        ultimo = con.execute("SELECT MAX(creato_il_utc) FROM batches").fetchone()[0]
    tipo, avviso = ambiente()
    return {
        "percorso": str(db), "dimensione_byte": db.stat().st_size if db.exists() else 0,
        "conteggi": conta, "ultimo_backup_utc": ub["valore"] if ub else None,
        "ultimo_batch_utc": ultimo, "ambiente": tipo, "avviso_ambiente": avviso,
    }


def segna_backup(db=None, ora=None):
    with _con(db, scrittura=True) as con:
        con.execute(
            "INSERT INTO meta(chiave, valore) VALUES ('ultimo_backup_utc', ?) "
            "ON CONFLICT(chiave) DO UPDATE SET valore = excluded.valore",
            (ora or ora_utc(),),
        )


def backup_bytes(db=None):
    """Copia coerente dell'intero archivio (anche se qualcuno sta scrivendo)."""
    db = Path(db) if db else percorso_db()
    with _con(db):
        pass  # assicura che il file e lo schema esistano
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        src = sqlite3.connect(str(db), timeout=15)
        dst = sqlite3.connect(tmp)
        try:
            src.backup(dst)
        finally:
            dst.close(); src.close()
        return Path(tmp).read_bytes()
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def esporta_csv(db=None):
    """Tutte le previsioni (non solo le primarie) con lo stato del risultato, in CSV leggibile."""
    import pandas as pd

    with _con(db) as con:
        df = pd.read_sql_query(
            """SELECT p.*, r.stato AS stato_risultato, r.gol_casa, r.gol_ospite
               FROM previsioni p LEFT JOIN risultati r ON r.match_key = p.match_key
               ORDER BY p.data_partita, p.match_key, p.motore, p.prediction_id""",
            con,
        )
    return df.to_csv(index=False).encode("utf-8")


def unisci_backup(db, contenuto):
    """Unisce un backup nell'archivio attuale SENZA cancellare né sovrascrivere nulla.

    Pensato per ripartire dopo un riavvio che ha azzerato il disco, ma sicuro anche
    su un archivio non vuoto: le righe già presenti restano com'erano, quelle mancanti
    vengono aggiunte, un risultato non ancora liquidato può essere completato.
    Ritorna i conteggi aggiunti; solleva ValueError se il file non è un backup valido.
    """
    if not contenuto or contenuto[:16] != b"SQLite format 3\x00":
        raise ValueError("il file non è un archivio SQLite")
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        Path(tmp).write_bytes(contenuto)
        try:
            chk = sqlite3.connect(tmp)
            try:
                ok = chk.execute("PRAGMA integrity_check").fetchone()[0]
                tab = {r[0] for r in chk.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            finally:
                chk.close()
        except sqlite3.DatabaseError as e:
            raise ValueError(f"archivio illeggibile: {e}") from e
        if ok != "ok":
            raise ValueError("il controllo di integrità del backup è fallito")
        mancanti = [t for t in TABELLE if t not in tab]
        if mancanti:
            raise ValueError("non è un backup di b-betting (mancano: " + ", ".join(mancanti) + ")")
        agg = {}
        with _con(db) as con:
            con.execute("ATTACH DATABASE ? AS bk", (tmp,))
            try:
                def comuni(tab, escludi=()):
                    a = [r[1] for r in con.execute(f"PRAGMA main.table_info({tab})")]
                    b = {r[1] for r in con.execute(f"PRAGMA bk.table_info({tab})")}
                    return ", ".join(c for c in a if c in b and c not in escludi)

                con.execute("BEGIN IMMEDIATE")
                try:
                    def conta(sql):
                        return con.execute(sql).rowcount

                    c = comuni("batches")
                    agg["batches"] = conta(f"INSERT OR IGNORE INTO main.batches({c}) SELECT {c} FROM bk.batches")
                    c = comuni("previsioni", escludi=("prediction_id",))
                    agg["previsioni"] = conta(
                        f"INSERT OR IGNORE INTO main.previsioni({c}) SELECT {c} FROM bk.previsioni "
                        "WHERE batch_id IN (SELECT batch_id FROM main.batches) ORDER BY prediction_id"
                    )
                    c = comuni("esclusioni")
                    agg["esclusioni"] = conta(f"INSERT OR IGNORE INTO main.esclusioni({c}) SELECT {c} FROM bk.esclusioni")
                    c = comuni("risultati")
                    agg["risultati"] = conta(f"INSERT OR IGNORE INTO main.risultati({c}) SELECT {c} FROM bk.risultati")
                    agg["risultati_completati"] = conta(
                        """UPDATE main.risultati SET stato = 'liquidata',
                             gol_casa = (SELECT b.gol_casa FROM bk.risultati b WHERE b.match_key = main.risultati.match_key),
                             gol_ospite = (SELECT b.gol_ospite FROM bk.risultati b WHERE b.match_key = main.risultati.match_key),
                             data_osservata = (SELECT b.data_osservata FROM bk.risultati b WHERE b.match_key = main.risultati.match_key),
                             fonte = (SELECT b.fonte FROM bk.risultati b WHERE b.match_key = main.risultati.match_key),
                             acquisito_il_utc = (SELECT b.acquisito_il_utc FROM bk.risultati b WHERE b.match_key = main.risultati.match_key),
                             nota = (SELECT b.nota FROM bk.risultati b WHERE b.match_key = main.risultati.match_key)
                           WHERE stato != 'liquidata'
                             AND match_key IN (SELECT match_key FROM bk.risultati WHERE stato = 'liquidata')"""
                    )
                    c = comuni("risultati_conflitti", escludi=("id",))
                    agg["risultati_conflitti"] = conta(
                        f"INSERT OR IGNORE INTO main.risultati_conflitti({c}) SELECT {c} FROM bk.risultati_conflitti"
                    )
                    con.execute("COMMIT")
                except BaseException:
                    try:
                        con.execute("ROLLBACK")
                    except sqlite3.Error:
                        pass
                    raise
            finally:
                con.execute("DETACH DATABASE bk")
        return agg
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
