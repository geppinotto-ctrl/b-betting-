import sys, os, time
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(AQUI, "stubs")); sys.path.insert(0, os.path.dirname(AQUI))
import streamlit as st
import requests
from unittest.mock import patch

ok = fail = 0
def check(nome, cond):
    global ok, fail
    if cond: ok += 1; print("  OK  ", nome)
    else: fail += 1; print("  FAIL", nome)

print("== config senza secrets.toml")
import config
check("import config non crasha senza secrets", config.ODDS_API_KEY == "")
check("ODDS_API_BASE di default invariato", config.ODDS_API_BASE == "https://odss-api.com/api/v1")

import resilienza as R
print("== valida_matches")
sporchi = [
    {"team1": "A", "team2": "B", "score": {"ft": [2, 1], "ht": [1, 0]}},
    {"team1": "A", "team2": "B", "score": {"ft": ["x", 1]}},
    {"team1": "A", "team2": "B", "score": {"ft": [1, 1], "ht": [2, 0]}},     # ht > ft
    {"team1": "A", "team2": "B"},                                             # senza score
    {"team1": "", "team2": "B"}, {"team1": None, "team2": "B"}, "spazzatura", None, 42,
    {"team1": "A", "team2": "B", "score": {"ft": [1, 2, 3]}},
    {"team1": "A", "team2": "B", "score": {"ft": [-1, 0]}},
    {"team1": "A", "team2": "B", "score": {"ft": [1.5, 0]}},
    {"team1": "A", "team2": "B", "score": {"ft": [float("nan"), 0]}},
    {"team1": "A", "team2": "B", "score": "2-1"},
]
v, scart, corr = R.valida_matches(sporchi)
check("scartate le partite senza squadre/non dict (5)", scart == 5)
check("ogni score è dict con ft/ht", all(isinstance(m["score"], dict) and "ft" in m["score"] for m in v))
check("ft sempre None o [int,int]", all(m["score"]["ft"] is None or (len(m["score"]["ft"]) == 2 and all(type(x) is int for x in m["score"]["ft"])) for m in v))
check("punteggio valido conservato", v[0]["score"]["ft"] == [2, 1] and v[0]["score"]["ht"] == [1, 0])
check("ht incoerente azzerato", v[2]["score"]["ht"] is None and v[2]["score"]["ft"] == [1, 1])
check("input non lista non crasha", R.valida_matches(None) == ([], 0, 0) and R.valida_matches({"a": 1}) == ([], 0, 0))

print("== http_get retry")
class Resp:
    def __init__(s, c, j=None): s.status_code = c; s._j = j
    def json(s):
        if s._j is None: raise ValueError("no json")
        return s._j
chiamate = []
def falso_get(seq):
    it = iter(seq)
    def g(url, **k):
        chiamate.append(url); x = next(it)
        if isinstance(x, Exception): raise x
        return x
    return g
with patch("resilienza.time.sleep"), patch("resilienza.requests.get", falso_get([requests.Timeout(), Resp(503), Resp(200, {"a": 1})])):
    chiamate.clear(); r = R.http_get("http://x/y")
    check("retry su timeout e 503, poi 200", r.status_code == 200 and len(chiamate) == 3)
with patch("resilienza.time.sleep"), patch("resilienza.requests.get", falso_get([Resp(404)])):
    chiamate.clear(); r = R.http_get("http://x/y")
    check("404 NON viene ritentato", r.status_code == 404 and len(chiamate) == 1)
with patch("resilienza.time.sleep"), patch("resilienza.requests.get", falso_get([requests.ConnectionError()] * 3)):
    try: R.http_get("http://x/y"); esito = "nessuna"
    except R.ErroreDati as e: esito = str(e)
    check("rete assente -> ErroreDati leggibile", "connessione" in esito)
try: R.json_sicuro(Resp(200, None)); esito = False
except R.ErroreDati: esito = True
check("JSON non valido -> ErroreDati", esito)

print("== sezione_sicura")
st_log_prima = len(st.LOG)
with R.sezione_sicura("Prova"):
    raise KeyError("boom")
check("eccezione assorbita + st.error mostrato", any(t == "error" and "Prova" in x for t, x in st.LOG[st_log_prima:]))
try:
    with R.sezione_sicura("Stop"):
        st.stop()
    passato = False
except SystemExit:
    passato = True
check("st.stop non viene inghiottito", passato)
print(f"\nRISULTATO core: {ok} ok, {fail} falliti"); sys.exit(1 if fail else 0)
