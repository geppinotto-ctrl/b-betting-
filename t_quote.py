import os, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(AQUI, "stubs")); sys.path.insert(0, os.path.dirname(AQUI))
import streamlit as st
from unittest.mock import patch
ok = fail = 0
def check(nome, cond):
    global ok, fail
    if cond: ok += 1; print("  OK  ", nome)
    else: fail += 1; print("  FAIL", nome)

st.secrets.presente = True            # qui la chiave c'è
import importlib, config; importlib.reload(config)
import resilienza as R, quote
importlib.reload(quote)

class Resp:
    def __init__(s, c, j=None): s.status_code = c; s._j = j; s.text = ""
    def json(s):
        if s._j is None: raise ValueError
        return s._j
def giu(url, **k): raise R.ErroreDati("timeout (odss-api.com)")

print("== test collegamento quote")
quote._testa_cached.clear()
with patch("quote.http_get", giu):
    t = quote.testa_odds_api()
check("API giù: ok=False con motivo, nessun crash", t["ok"] is False and "timeout" in t["errore"])
check("fallimento NON in cache per 1 ora", quote._testa_cached.calls() == 0)
with patch("quote.http_get", lambda *a, **k: Resp(401, {})):
    t = quote.testa_odds_api()
check("401 -> messaggio sulla chiave non valida", "non valida" in t["errore"])
with patch("quote.http_get", lambda *a, **k: Resp(200, {"bookmakers": []})):
    t = quote.testa_odds_api()
check("200 -> ok, e questo sì viene messo in cache", t["ok"] and quote._testa_cached.calls() == 1)

print("== liste quote: risposte incomplete o assenti")
for nome, risposta in [("JSON non valido", Resp(200, None)), ("lista vuota", Resp(200, [])),
                       ("dict senza odds", Resp(200, {"x": 1})), ("odds non lista", Resp(200, {"odds": "boh"})),
                       ("eventi senza squadre", Resp(200, {"odds": [{"id": 1}, "x", None]}))]:
    with patch("quote.http_get", lambda *a, r=risposta, **k: r):
        res = quote._scarica_lista_quote("K")
    check(f"{nome}: nessun crash, odds è lista pulita", isinstance(res["odds"], list) and res["odds"] == [])
with patch("quote.http_get", lambda *a, **k: Resp(429)):
    res = quote._scarica_lista_quote("K")
check("HTTP 429 (limite richieste) -> errore leggibile", res["ok"] is False and "429" in res["errore"])
with patch("quote.http_get", giu):
    res = quote._scarica_lista_quote("K")
check("rete giù -> ok False", res["ok"] is False)
quote._quote_lista_cached.clear()
with patch("quote.http_get", giu):
    r1 = quote.carica_quote_api("K")
check("carica_quote_api: errore non in cache", r1["ok"] is False and quote._quote_lista_cached.calls() == 0)

print("== catalogo con quote malformate")
rec = [{"market": "1x2", "bookmakers": [
    {"key": "A", "playable_it": True, "outcomes": {"home": "2.10", "draw": "nan", "away": "inf"}},
    {"key": "B", "playable_it": True, "outcomes": ["non", "un", "dict"]},
    {"key": "C", "playable_it": True, "outcomes": None},
    {"key": "D", "playable_it": True, "outcomes": {"home": 0.9, "draw": "abc", "away": 3.4}},
    "stringa", None]}, "non un record", {"market": "ou", "line": "2.5", "bookmakers": "boh"}, {}]
cat = quote.costruisci_catalogo(rec, True)
check("nessun crash", isinstance(cat, dict))
check("NaN/inf/<=1/non numeriche scartate", set(cat.get("Esito finale 1X2", {})) == {"1", "2"})
check("quote valide mantenute", cat["Esito finale 1X2"]["1"] == {"A": 2.1} and cat["Esito finale 1X2"]["2"] == {"D": 3.4})
check("catalogo vuoto con input assurdi", quote.costruisci_catalogo(None) == {} and quote.costruisci_catalogo("x") == {})

print("== ottieni_catalogo_partita non solleva mai")
def esplode(*a, **k): raise RuntimeError("bug imprevisto")
with patch("quote.carica_quote_api", esplode):
    cat, ev, avviso, recs = quote.ottieni_catalogo_partita("Inter", "Milan")
check("bug interno -> (None, None, avviso, []) invece di crash", cat is None and "non elaborabili" in avviso and recs == [])
with patch("quote.carica_quote_api", lambda k: {"ok": False, "errore": "timeout", "odds": [], "chiavi": []}):
    cat, ev, avviso, recs = quote.ottieni_catalogo_partita("Inter", "Milan")
check("API giù -> avviso 'Errore API quote'", cat is None and "timeout" in avviso)
ev = {"home_team": "Inter", "away_team": "Milan", "event_id": "7", "bookmakers": []}
with patch("quote.carica_quote_api", lambda k: {"ok": True, "errore": "", "odds": [ev], "chiavi": []}), \
     patch("quote.carica_mercati_evento", lambda k, e: {"ok": False, "errore": "HTTP 500", "records": []}):
    cat, e2, avviso, recs = quote.ottieni_catalogo_partita("Inter", "Milan")
check("mercati extra assenti -> degrada all'1X2 con avviso", "Altri mercati non disponibili" in avviso and e2 is ev)
quote.st.secrets.presente = False
print(f"\nRISULTATO quote: {ok} ok, {fail} falliti"); sys.exit(1 if fail else 0)
