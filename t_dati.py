import os, sys, json
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(AQUI, "stubs")); sys.path.insert(0, os.path.dirname(AQUI))
import streamlit as st
from datetime import timedelta
from unittest.mock import patch

ok = fail = 0
def check(nome, cond):
    global ok, fail
    if cond: ok += 1; print("  OK  ", nome)
    else: fail += 1; print("  FAIL", nome)

import resilienza as R, dati, modello, quote
from config import adesso, campionati_disponibili

class Resp:
    def __init__(s, c, j=None): s.status_code = c; s._j = j; s.content = b""
    def json(s):
        if s._j is None: raise ValueError
        return s._j

def lega(anno=2026, extra=None, futuro=True):
    sq = [f"Squadra{i}" for i in range(6)]
    ms = []
    for g in range(30):
        a, b = sq[g % 6], sq[(g * 2 + 1) % 6]
        if a == b: b = sq[(g + 1) % 6]
        ms.append({"round": f"G{g}", "date": f"{anno}-09-{(g % 27) + 1:02d}", "team1": a, "team2": b,
                   "score": {"ft": [g % 4, (g * 3) % 3], "ht": [0, 0]}})
    if futuro:
        d = (adesso() + timedelta(days=2)).strftime("%Y-%m-%d")
        ms.append({"round": "F", "date": d, "team1": "Squadra0", "team2": "Squadra1"})
    return {"matches": ms + (extra or [])}

def rete_giu(url, **k): raise R.ErroreDati("connessione non riuscita (x)")
def rete_ok(payload):
    return lambda url, **k: Resp(200, payload)

print("== cache NON avvelenata da un timeout")
dati._campionato_cached.clear(); dati._ULTIMO_BUONO.clear()
with patch("dati.http_get", rete_giu):
    r1 = dati.carica_dati_campionato("Italia - Serie A", "2026-27")
check("rete giù: nessun crash, stato errore, matches []", r1["stato"] == R.ERRORE and r1["matches"] == [])
check("messaggio chiaro per l'utente", "impossibile scaricare" in r1["messaggio"])
check("l'errore NON è finito in cache", dati._campionato_cached.calls() == 0)
with patch("dati.http_get", rete_ok(lega())):
    r2 = dati.carica_dati_campionato("Italia - Serie A", "2026-27")
check("rete tornata: dati subito disponibili (vecchio codice: vuoti per 30 min)", r2["stato"] == R.OK and len(r2["matches"]) == 31)

print("== fallback sull'ultimo dato buono")
dati._campionato_cached.clear()                       # simula "Aggiorna Dati"
with patch("dati.http_get", rete_giu):
    r3 = dati.carica_dati_campionato("Italia - Serie A", "2026-27")
check("aggiornamento fallito -> stato obsoleto con dati vecchi", r3["stato"] == R.OBSOLETO and len(r3["matches"]) == 31)
check("il messaggio dice da quando sono i dati", "ultimi dati validi" in r3["messaggio"])

print("== stagione assente / dati sporchi / stagione sbagliata")
dati._campionato_cached.clear(); dati._ULTIMO_BUONO.clear()
with patch("dati.http_get", lambda url, **k: Resp(404)):
    r = dati.carica_dati_campionato("Italia - Serie A", "2026-27")
check("tutti 404 -> vuoto (non errore), nessun crash", r["stato"] == R.VUOTO and r["matches"] == [])
dati._campionato_cached.clear()
sporco = lega(extra=[{"team1": "X"}, "junk", {"team1": "A", "team2": "B", "score": {"ft": ["a", 1]}}])
with patch("dati.http_get", rete_ok(sporco)):
    r = dati.carica_dati_campionato("Italia - Serie A", "2026-27")
check("righe sporche -> stato parziale con conteggio", r["stato"] == R.PARZIALE and r["scartate"] == 2 and r["corretti"] == 1)
check("tutti i punteggi sono ora sicuri da indicizzare", all(m["score"]["ft"] is None or len(m["score"]["ft"]) == 2 for m in r["matches"]))
dati._campionato_cached.clear(); dati._ULTIMO_BUONO.clear()
with patch("dati.http_get", rete_ok(lega(anno=2019))):
    r = dati.carica_dati_campionato("Italia - Serie A", "2026-27")
check("dati di un'altra stagione rifiutati (non mostrati come 2026-27)", r["matches"] == [] and r["stato"] == R.VUOTO)

print("== Champions League (ESPN): un anno fallisce -> niente risultato parziale in cache")
dati._campionato_cached.clear(); dati._ULTIMO_BUONO.clear()
evento = {"id": "1", "date": "2026-10-20T19:00Z", "competitions": [{"competitors": [
    {"homeAway": "home", "team": {"displayName": "Inter"}, "score": "2"},
    {"homeAway": "away", "team": {"displayName": "Real"}, "score": "1"}]}],
    "status": {"type": {"completed": True, "state": "post"}}}
def espn(url, params=None, **k):
    if params and params.get("dates") == "2027": raise R.ErroreDati("timeout (espn)")
    return Resp(200, {"events": [evento]})
with patch("dati.http_get", espn):
    r = dati.carica_dati_campionato("UEFA Champions League", "2026-27")
check("anno 2 fallito -> errore dichiarato, non dati dimezzati", r["stato"] == R.ERRORE)
check("... e non memorizzato", dati._campionato_cached.calls() == 0)
with patch("dati.http_get", lambda url, params=None, **k: Resp(200, {"events": [evento]})):
    r = dati.carica_dati_campionato("UEFA Champions League", "2026-27")
check("CL con entrambi gli anni ok", r["stato"] == R.OK and len(r["matches"]) == 1 and r["matches"][0]["score"]["ft"] == [2, 1])

print("== stats extra")
dati._stats_cached.clear(); dati._ULTIME_STATS.clear()
csv = b"HomeTeam,AwayTeam,HC,AC\nA,B,5,3\nC,D,4,6\n"
def csv_resp(url, **k): x = Resp(200); x.content = csv; return x
with patch("dati.http_get", rete_giu):
    df = dati.carica_stats_extra("Italia - Serie A", "2026-27")
check("rete giù -> None, nessun crash, non in cache", df is None and dati._stats_cached.calls() == 0)
with patch("dati.http_get", csv_resp):
    df = dati.carica_stats_extra("Italia - Serie A", "2026-27")
check("CSV valido caricato", df is not None and len(df) == 2)
dati._stats_cached.clear()
with patch("dati.http_get", rete_giu):
    df2 = dati.carica_stats_extra("Italia - Serie A", "2026-27")
check("aggiornamento fallito -> ultimo CSV valido", df2 is not None and len(df2) == 2)
dati._stats_cached.clear()
def csv_rotto(url, **k): x = Resp(200); x.content = b"colonna1,colonna2\n1,2\n"; return x
with patch("dati.http_get", csv_rotto):
    check("CSV senza colonne attese -> None", dati.carica_stats_extra("Spagna - La Liga", "2026-27") is None)
check("Champions (nessuna fonte stats) -> None senza chiamate", dati.carica_stats_extra("UEFA Champions League", "2026-27") is None)

print("== AI Advice / Home: un torneo giù non rompe gli altri e non avvelena la cache")
dati._campionato_cached.clear(); dati._ULTIMO_BUONO.clear(); dati._stats_cached.clear(); dati._ULTIME_STATS.clear()
modello._consigli_cached.clear()
def mista(url, params=None, **k):
    if "en.1" in url or "spain" in url or "es.1" in url: raise R.ErroreDati("timeout")
    if "football-data" in url: raise R.ErroreDati("timeout")
    if "espn" in url: raise R.ErroreDati("timeout")
    return Resp(200, lega())
with patch("dati.http_get", mista), patch("modello.adesso", adesso):
    c = modello.raccogli_consigli("2026-27", 7, False)
check("restituisce i consigli dei tornei funzionanti", len(c) > 0 and all(x["campionato"] in campionati_disponibili for x in c))
check("risultato parziale NON in cache", modello._consigli_cached.calls() == 0)
modello._consigli_cached.clear()
with patch("dati.http_get", lambda url, params=None, **k: Resp(200, lega()) if "espn" not in url and "football-data" not in url else (_ for _ in ()).throw(R.ErroreDati("x"))):
    pass
dati._campionato_cached.clear(); dati._ULTIMO_BUONO.clear(); dati._stats_cached.clear()
def tutto_ok(url, params=None, **k):
    if "espn" in url: return Resp(200, {"events": []})
    if "football-data" in url: x = Resp(404); return x
    return Resp(200, lega())
with patch("dati.http_get", tutto_ok):
    c2 = modello.raccogli_consigli("2026-27", 7, False)
check("con tutti i dati ok il risultato viene messo in cache", modello._consigli_cached.calls() == 1 and len(c2) > 0)

print("== cache selettiva")
quote._quote_lista_cached.clear()
quote._quote_lista_cached.__wrapped__ if hasattr(quote._quote_lista_cached, "__wrapped__") else None
# riempio la cache quote con un valore finto
with patch("quote._scarica_lista_quote", lambda k: {"ok": True, "errore": "", "odds": [], "chiavi": []}):
    quote._quote_lista_cached("K")
check("cache quote popolata", quote._quote_lista_cached.calls() == 1)
R.svuota_cache("download", "calcoli")
check("Aggiorna Dati: svuota download e calcoli", dati._campionato_cached.calls() == 0 and modello._consigli_cached.calls() == 0)
check("... ma NON le quote API (risparmio richieste)", quote._quote_lista_cached.calls() == 1)
R.svuota_quote()
check("svuota_quote le cancella solo su richiesta", quote._quote_lista_cached.calls() == 0)

print("== calcolo con progresso")
st.session_state.clear(); st.LOG.clear()
r = R.calcolo_con_progresso("k", lambda av: (av(0.5, "meta"), "RIS")[1], "Calcolo", salva=True)
check("barra aggiornata durante il calcolo e chiusa", any("50%" in x for t, x in st.LOG if t == "progress") and st.LOG[-1] == ("progress", "vuota"))
check("risultato memorizzato (seconda chiamata istantanea)", R.calcolo_con_progresso("k", lambda av: 1/0, "Calcolo") == "RIS")
R.calcolo_con_progresso("k2", lambda av: "X", "Calcolo", salva=False)
check("salva=False (dati incompleti) non memorizza", "k2" not in st.session_state["_calcoli"])
try: R.calcolo_con_progresso("k3", lambda av: 1/0, "Calcolo"); e = False
except ZeroDivisionError: e = True
check("errore nel calcolo sale al chiamante e la barra si chiude", e and st.LOG[-1] == ("progress", "vuota"))

print(f"\nRISULTATO dati: {ok} ok, {fail} falliti"); sys.exit(1 if fail else 0)
