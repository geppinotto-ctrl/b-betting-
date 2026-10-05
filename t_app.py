import sys, runpy, traceback, os
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(AQUI, "stubs")); sys.path.insert(0, os.path.dirname(AQUI))
os.chdir(os.path.dirname(AQUI))
import streamlit as st
from unittest.mock import patch
import resilienza as R

def giu(url, **k): raise R.ErroreDati("connessione non riuscita (test)")

import dati as _dati
def esegui(nome, pagina, rete):
    st.session_state.clear(); st.LOG.clear()
    R.svuota_cache("download", "calcoli"); _dati._ULTIMO_BUONO.clear(); _dati._ULTIME_STATS.clear()
    st.session_state.pagina = pagina
    st.session_state.stagione = "2026-27"; st.session_state.torneo = "Italia - Serie A"
    st.session_state.motore = "Poisson"
    try:
        with patch("resilienza.http_get", rete), patch("dati.http_get", rete), patch("quote.http_get", rete):
            runpy.run_path("app.py", run_name="__main__")
        esito = "completata"
    except SystemExit:
        esito = "completata (st.stop)"
    except Exception:
        esito = "CRASH:\n" + traceback.format_exc()
    errori = [x for t, x in st.LOG if t == "error"]
    avvisi = [x for t, x in st.LOG if t == "warning"]
    print(f"\n[{nome}] -> {esito}")
    prog = [x for t, x in st.LOG if t == "progress" and x != "vuota"]
    print(f"   st.error: {len(errori)} | st.warning: {len(avvisi)} | aggiornamenti barra: {len(prog)}")
    for x in errori[:8]: print("   ERR :", x[:150])
    for x in avvisi[:5]: print("   WARN:", x[:150])
    return esito.startswith("completata")

import json
from datetime import timedelta
from config import adesso
def lega_grande():
    sq = [f"Squadra{i}" for i in range(10)]
    ms, k = [], 0
    for giro in range(10):
        for i in range(10):
            a, b = sq[i], sq[(i + 1 + giro) % 10]
            if a == b: continue
            k += 1
            ms.append({"round": f"G{giro+1}", "date": f"2026-0{(k % 3) + 1}-{(k % 27) + 1:02d}", "team1": a, "team2": b,
                       "score": {"ft": [(k * 7) % 4, (k * 5) % 3], "ht": [(k * 7) % 2, 0]}})
    d = (adesso() + timedelta(days=3)).strftime("%Y-%m-%d")
    ms += [{"round": "F", "date": d, "team1": "Squadra0", "team2": "Squadra1"}]
    return {"matches": ms}
class Resp:
    def __init__(s, c, j=None): s.status_code = c; s._j = j; s.content = b""
    def json(s): return s._j
def ok_rete(url, **k):
    if "football-data" in url or "espn" in url: return Resp(404)
    return Resp(200, lega_grande())
def mezzo_rotta(url, **k):
    if "raw.githubusercontent" in url: return Resp(200, {"matches": lega_grande()["matches"] + ["JUNK", {"team1": "X"}, {"team1": "Q", "team2": "Z", "score": {"ft": "boh"}}]})
    raise R.ErroreDati("timeout (secondaria)")

risultati = [
    esegui("HOME, rete GIÙ", "home", giu),
    esegui("DASHBOARD, rete GIÙ", "dashboard", giu),
    esegui("DASHBOARD, dati completi", "dashboard", ok_rete),
    esegui("DASHBOARD, dati sporchi + fonti secondarie giù", "dashboard", mezzo_rotta),
    esegui("HOME, dati completi", "home", ok_rete),
]
sys.exit(0 if all(risultati) else 1)
