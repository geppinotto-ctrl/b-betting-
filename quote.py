from datetime import datetime, timedelta
import difflib
import pandas as pd
import re
import requests
import streamlit as st
import time as _time
from config import ODDS_API_KEY, adesso, stagione_corrente, torneo_corrente
from dati import normalizza_nome


@st.cache_data(ttl=3600, show_spinner=False)
def testa_odds_api():
    if not ODDS_API_KEY:
        return {
            "ok": False,
            "errore": "Chiave ODDS_API_KEY non trovata nei Secrets."
        }

    url = "https://odss-api.com/api/v1/bookmakers"

    try:
        r = requests.get(
            url,
            headers={"x-api-key": ODDS_API_KEY},
            timeout=8
        )

        if r.status_code != 200:
            return {
                "ok": False,
                "errore": f"HTTP {r.status_code}"
            }

        data = r.json()

        if isinstance(data, dict):
            return {
                "ok": True,
                "dati": data
            }

        return {
            "ok": False,
            "errore": "Risposta API non riconosciuta."
        }

    except Exception as e:
        return {
            "ok": False,
            "errore": str(e)
        }


ALIAS_SQUADRE = {
    "internazionale milano": "inter",
    "internazionale": "inter",
    "inter milan": "inter",
    "manchester utd": "manchester united",
    "man united": "manchester united",
    "man city": "manchester city",
    "tottenham hotspur": "tottenham",
    "spurs": "tottenham",
    "wolves": "wolverhampton wanderers",
    "newcastle": "newcastle united",
    "west ham": "west ham united",
    "brighton hove albion": "brighton",
    "atletico madrid": "atletico",
    "paris saint germain": "psg",
    "paris sg": "psg",
}


def _canon_squadra(nome):
    n = normalizza_nome(nome)
    return ALIAS_SQUADRE.get(n, n)


def _simili(a, b):
    ca, cb = _canon_squadra(a), _canon_squadra(b)
    if not ca or not cb:
        return 0.0
    if ca == cb:
        return 1.0
    return difflib.SequenceMatcher(None, ca, cb).ratio()


def trova_evento_quote(odds_list, casa, ospite, soglia=0.8):
    """Sceglie l'evento che somiglia di più, richiedendo che entrambe le squadre combacino."""
    migliore, punteggio = None, 0.0
    for ev in odds_list:
        if not isinstance(ev, dict):
            continue
        sc = min(
            _simili(casa, ev.get("home_team", "")),
            _simili(ospite, ev.get("away_team", "")),
        )
        if sc > punteggio:
            migliore, punteggio = ev, sc
    if punteggio >= soglia:
        return migliore, punteggio
    return None, punteggio


def _quota(v):
    try:
        return float(v)
    except Exception:
        return None


ORDINE_MERCATI = [
    "Esito finale 1X2", "Doppia chance", "Under/Over", "Goal/No Goal",
    "Parziale/finale", "Risultato esatto", "Somma gol", "Pari/dispari",
    "Altri mercati",
]


LINEE_OU = (1.5, 2.5, 3.5, 4.5)


SCEGLI_AUTO = "Migliore quota (automatica)"


URL_ODDS = "https://odss-api.com/api/v1/odds"


_MAP_1X2 = {"home": "1", "1": "1", "draw": "X", "x": "X", "away": "2", "2": "2"}


_MAP_PD = {"pari": "Pari", "even": "Pari", "dispari": "Dispari", "odd": "Dispari"}


_ESCLUDI = (
    "primotempo", "secondotempo", "1t", "2t", "1tempo", "2tempo", "firsthalf",
    "secondhalf", "1sthalf", "2ndhalf", "casa", "ospite", "home", "away",
    "squadra", "team", "corner", "angol", "cart", "card", "giocator", "player",
)


def _chiave_testo(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _linea_num(v):
    try:
        return round(float(v), 2)
    except Exception:
        return None


def _pulisci_esito(k):
    return str(k).strip().replace("_", " ").replace(":", "-")


def _mappa_dc(k):
    kk = _chiave_testo(k)
    if kk in ("1x", "x1") or ("home" in kk and "draw" in kk):
        return "1X"
    if kk in ("x2", "2x") or ("draw" in kk and "away" in kk):
        return "X2"
    if kk == "12" or ("home" in kk and "away" in kk):
        return "12"
    return None


def _mappa_btts(k):
    kk = _chiave_testo(k)
    if kk in ("no", "ng", "nogoal") or kk.startswith("no"):
        return "No Goal"
    if kk in ("yes", "si", "gg", "goal") or kk.startswith(("yes", "si", "gg")):
        return "Goal"
    return None


def _mappa_ou(k, linea):
    kk = _chiave_testo(k)
    if kk.startswith("over") or kk == "o":
        return f"Over {linea:g}"
    if kk.startswith("under") or kk == "u":
        return f"Under {linea:g}"
    return None


def _pulisci_htft(k):
    tok = re.findall(r"[a-z0-9]+", str(k).lower())
    m = {"home": "1", "draw": "X", "away": "2", "1": "1", "x": "X", "2": "2"}
    if len(tok) == 1 and len(tok[0]) == 2 and all(c in "1x2" for c in tok[0]):
        tok = list(tok[0])
    if len(tok) == 2:
        return "/".join(m.get(t, t) for t in tok)
    return _pulisci_esito(k)


def _categoria_altro(label):
    k = _chiave_testo(label)
    if any(x in k for x in ("parzialefinale", "parzfin", "htft", "halftimefulltime",
                            "primotempofinale", "1tfinale")):
        return "Parziale/finale"
    if any(x in k for x in _ESCLUDI):
        return "Altri mercati"
    if "dispari" in k or "oddeven" in k:
        return "Pari/dispari"
    if any(x in k for x in ("risultatoesatto", "correctscore", "exactscore", "esatto")):
        return "Risultato esatto"
    if (any(x in k for x in ("sommagol", "sommagoal", "totalgoals", "totalegol",
                             "goltotali", "numerogol", "numerodigol", "totalgol"))
            and "overunder" not in k and "underover" not in k):
        return "Somma gol"
    return "Altri mercati"


def _periodo_parziale(p):
    """True se il mercato riguarda solo un tempo/supplementari (non la partita intera)."""
    if not p:
        return False
    k = _chiave_testo(p)
    return bool(k) and any(x in k for x in (
        "half", "1st", "2nd", "primotempo", "secondotempo", "1t", "2t",
        "1h", "2h", "extra", "penalt", "overtime", "quarter",
    ))


def _scope_speciale(sc):
    """True per scope diversi da 'partita intera' (es. team, player)."""
    if not sc:
        return False
    k = _chiave_testo(sc)
    return bool(k) and k not in ("match", "game", "full", "fulltime", "event", "regular", "total", "all")


def _nome_periodo(p):
    k = _chiave_testo(p)
    if k in ("1sthalf", "firsthalf", "1h", "primotempo", "1t"):
        return "1° tempo"
    if k in ("2ndhalf", "secondhalf", "2h", "secondotempo", "2t"):
        return "2° tempo"
    return str(p)


def _classifica_record(rec):
    """Ritorna (categoria, funzione che trasforma l'esito dell'API in etichetta)."""
    mk = str(rec.get("market", "")).strip()
    mkl = mk.lower()
    linea = _linea_num(rec.get("line"))
    periodo, scope = rec.get("period"), rec.get("scope")
    nome = mk.split(":", 1)[1].strip() if ":" in mk else mk.upper()
    parziale = _periodo_parziale(periodo)
    speciale = _scope_speciale(scope)
    parti = []
    if linea is not None:
        parti.append(f"{linea:g}")
    if parziale:
        parti.append(_nome_periodo(periodo))
    if speciale:
        parti.append(str(scope))
    extra = " ".join(parti)
    generico = bool(parziale or speciale or rec.get("player"))

    def altro(k):
        return f"{nome} {extra}".strip() + ": " + _pulisci_esito(k)

    if not generico:
        if mkl == "1x2":
            return "Esito finale 1X2", lambda k: _MAP_1X2.get(_chiave_testo(k))
        if mkl == "dc":
            return "Doppia chance", _mappa_dc
        if mkl == "btts":
            return "Goal/No Goal", _mappa_btts
        if mkl == "ou" and linea in LINEE_OU:
            return "Under/Over", (lambda k, l=linea: _mappa_ou(k, l))
        if mkl not in ("1x2", "dc", "btts", "ou", "ah", "eh", "moneyline"):
            cat = _categoria_altro(nome)
            if cat == "Parziale/finale":
                return cat, _pulisci_htft
            if cat == "Risultato esatto":
                return cat, (lambda k: re.sub(r"[\s:_]+", "-", str(k).strip()))
            if cat == "Somma gol":
                return cat, _pulisci_esito
            if cat == "Pari/dispari":
                return cat, (lambda k: _MAP_PD.get(_chiave_testo(k)))
    return "Altri mercati", altro


def costruisci_catalogo(records, solo_italia=True):
    """{mercato: {giocata: {bookmaker: quota}}}"""
    cat = {}
    for rec in records or []:
        if not isinstance(rec, dict):
            continue
        categoria, mappa = _classifica_record(rec)
        for bm in rec.get("bookmakers") or []:
            if not isinstance(bm, dict):
                continue
            if solo_italia and bm.get("playable_it") is False:
                continue
            nome_bm = str(bm.get("key", "N/D"))
            for k, v in (bm.get("outcomes") or {}).items():
                q = _quota(v)
                if q is None or q <= 1.0:
                    continue
                etichetta = mappa(k)
                if not etichetta:
                    continue
                d = cat.setdefault(categoria, {}).setdefault(etichetta, {})
                if q > d.get(nome_bm, 0):
                    d[nome_bm] = q
    return cat


def _ordine_giocata(categoria, etichetta):
    if categoria == "Under/Over":
        m = re.match(r"(Over|Under) ([0-9.]+)", etichetta)
        if m:
            return (0, float(m.group(2)), 0 if m.group(1) == "Over" else 1, "")
    fissi = {
        "Esito finale 1X2": ["1", "X", "2"],
        "Doppia chance": ["1X", "X2", "12"],
        "Goal/No Goal": ["Goal", "No Goal"],
        "Pari/dispari": ["Pari", "Dispari"],
    }
    if etichetta in fissi.get(categoria, []):
        return (0, fissi[categoria].index(etichetta), 0, "")
    nat = [(0, int(t)) if t.isdigit() else (1, t)
           for t in re.split(r"(\d+)", etichetta) if t != ""]
    return (1, 0, 0, nat)


def etichetta_slip(mercato, giocata):
    if mercato == "Esito finale 1X2":
        return f"1X2: {giocata}"
    if mercato == "Parziale/finale":
        return f"Parz/Fin {giocata}"
    if mercato == "Risultato esatto":
        return f"Ris. esatto {giocata}"
    if mercato == "Somma gol":
        return f"Somma gol {giocata}"
    if mercato == "Pari/dispari":
        return f"Gol {giocata}"
    return giocata


def _scarica_lista_quote(chiave):
    try:
        r = requests.get(
            URL_ODDS,
            params={"sport": "calcio", "market": "1x2", "state": "prematch", "limit": 2000},
            headers={"x-api-key": chiave},
            timeout=15,
        )
    except Exception as e:
        return {"ok": False, "errore": str(e), "odds": [], "chiavi": []}
    if r.status_code != 200:
        return {"ok": False, "errore": f"HTTP {r.status_code} - {r.text[:150]}", "odds": [], "chiavi": []}
    try:
        data = r.json()
    except Exception:
        return {"ok": False, "errore": "Risposta non in formato JSON.", "odds": [], "chiavi": []}
    if isinstance(data, dict):
        odds, chiavi = data.get("odds", []), list(data.keys())
    elif isinstance(data, list):
        odds, chiavi = data, []
    else:
        odds, chiavi = [], []
    return {"ok": True, "errore": "", "odds": odds if isinstance(odds, list) else [], "chiavi": chiavi}


@st.cache_data(ttl=1800, show_spinner=False)
def _quote_lista_cached(chiave):
    ris = _scarica_lista_quote(chiave)
    if not ris["ok"]:
        raise RuntimeError(ris["errore"])  # gli errori non finiscono in cache
    return ris


def carica_quote_api(chiave):
    """Lista eventi con 1X2 (ogni 30 minuti al massimo, per risparmiare richieste)."""
    ultimo = st.session_state.get("_quote_fail")
    if ultimo and _time.time() - ultimo[0] < 60:
        return ultimo[1]
    try:
        ris = _quote_lista_cached(chiave)
        st.session_state.pop("_quote_fail", None)
        return ris
    except Exception as e:
        ris = {"ok": False, "errore": str(e), "odds": [], "chiavi": []}
        st.session_state["_quote_fail"] = (_time.time(), ris)
        return ris


def _scarica_mercati_evento(chiave, event_id):
    try:
        r = requests.get(
            URL_ODDS,
            params={"event_id": event_id, "content": "match", "limit": 5000},
            headers={"x-api-key": chiave},
            timeout=15,
        )
    except Exception as e:
        return {"ok": False, "errore": str(e), "records": []}
    if r.status_code != 200:
        return {"ok": False, "errore": f"HTTP {r.status_code} - {r.text[:200]}", "records": []}
    try:
        data = r.json()
    except Exception:
        return {"ok": False, "errore": "Risposta non in formato JSON.", "records": []}
    recs = data.get("odds", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    return {"ok": True, "errore": "", "records": recs if isinstance(recs, list) else []}


@st.cache_data(ttl=1800, show_spinner=False)
def _mercati_cached(chiave, event_id):
    ris = _scarica_mercati_evento(chiave, event_id)
    if not ris["ok"]:
        raise RuntimeError(ris["errore"])
    return ris


def carica_mercati_evento(chiave, event_id):
    """Tutti i mercati di una partita: una richiesta ogni 30 minuti per partita."""
    falliti = st.session_state.setdefault("_mercati_fail", {})
    ultimo = falliti.get(event_id)
    if ultimo and _time.time() - ultimo[0] < 60:
        return ultimo[1]
    try:
        ris = _mercati_cached(chiave, event_id)
        falliti.pop(event_id, None)
        return ris
    except Exception as e:
        ris = {"ok": False, "errore": str(e), "records": []}
        falliti[event_id] = (_time.time(), ris)
        return ris


def ottieni_catalogo_partita(casa, ospite, solo_italia=True):
    """Ritorna (catalogo, evento, avviso, records)."""
    if not ODDS_API_KEY:
        return None, None, "Chiave ODDS_API_KEY non trovata nei Secrets.", []
    res = carica_quote_api(ODDS_API_KEY)
    if not res["ok"]:
        return None, None, f"Errore API quote: {res['errore']}", []
    evento, _ = trova_evento_quote(res["odds"], casa, ospite)
    if evento is None:
        return None, None, (
            "Quote non trovate per questa partita: di solito sono disponibili "
            "solo per le gare dei prossimi giorni."
        ), []
    records, avviso = [evento], ""
    eid = evento.get("event_id")
    if eid:
        ris = carica_mercati_evento(ODDS_API_KEY, str(eid))
        if ris["ok"] and ris["records"]:
            records = ris["records"]
        else:
            avviso = f"Altri mercati non disponibili ({ris['errore'] or 'nessun dato'}): mostro solo l'1X2."
    cat = costruisci_catalogo(records, solo_italia)
    if not cat and solo_italia:
        cat = costruisci_catalogo(records, False)
        if cat:
            avviso = (avviso + " Nessun bookmaker italiano con queste quote: mostro tutti.").strip()
    return cat, evento, avviso, records


def aggiungi_alla_schedina(partita, giocata, quota, chiave_msg):
    nuova = pd.DataFrame([{
        "Partita": partita,
        "Giocata": giocata,
        "Quota": float(quota),
        "Vinta": True,
        "Elimina": False,
    }])
    base = st.session_state.get("slip_df")
    if base is None or len(base) == 0:
        st.session_state.slip_df = nuova
    else:
        st.session_state.slip_df = pd.concat([base, nuova], ignore_index=True)
    st.session_state.slip_ver = st.session_state.get("slip_ver", 0) + 1
    st.session_state[chiave_msg] = f"Aggiunta alla schedina: {partita} · {giocata} @ {float(quota):.2f}"
    st.rerun()


def selettore_giocata(cat, prefisso):
    """Mercato -> Giocata -> Bookmaker. Ritorna (mercato, giocata, quota, bookmaker)."""
    mercati = [m for m in ORDINE_MERCATI if m in cat]
    mercato = st.selectbox("Mercato", mercati, key=f"{prefisso}_mercato")
    giocate = sorted(cat[mercato].keys(), key=lambda g: _ordine_giocata(mercato, g))
    mk = _chiave_testo(mercato)
    giocata = st.selectbox("Giocata", giocate, key=f"{prefisso}_giocata_{mk}")
    per_book = cat[mercato][giocata]
    ordinati = sorted(per_book.items(), key=lambda x: -x[1])
    opzioni = [SCEGLI_AUTO] + [f"{b} · {q:.2f}" for b, q in ordinati]
    scelta = st.selectbox(
        "Bookmaker", opzioni, key=f"{prefisso}_book_{mk}_{_chiave_testo(giocata)}"
    )
    if scelta == SCEGLI_AUTO or scelta not in opzioni:
        book, quota = ordinati[0]
    else:
        book, quota = ordinati[opzioni.index(scelta) - 1]
    c1, c2 = st.columns(2)
    c1.metric("Quota", f"{quota:.2f}")
    c2.caption(f"Bookmaker: **{book}**  \n{len(per_book)} bookmaker con questa giocata")
    return mercato, giocata, quota, book


def mostra_quote_prepartita(tab, matches):
    with tab:
        st.subheader("💰 Quote Prepartita")
        st.caption(
            "Confronto quote tra i bookmaker: 1X2, doppia chance, under/over, "
            "goal/no goal e gli altri mercati disponibili."
        )
        if not matches:
            st.info("Nessuna partita disponibile.")
            return

        periodo = st.selectbox(
            "Periodo",
            ["Prossimi 7 giorni", "Prossimi 14 giorni", "Prossimi 30 giorni"],
            key=f"quote_periodo_{torneo_corrente()}_{stagione_corrente()}",
        )
        oggi = adesso().date()
        limite = oggi + timedelta(days=int(periodo.split()[1]))

        candidate = []
        for m in matches:
            if not isinstance(m, dict) or not m.get("team1") or not m.get("team2"):
                continue
            try:
                d = datetime.strptime(str(m.get("date", ""))[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
            if oggi <= d <= limite:
                candidate.append((d, m))
        candidate.sort(key=lambda x: (x[0], str(x[1].get("time") or "")))
        if not candidate:
            st.info("Nessuna partita nel periodo scelto.")
            return

        per_etichetta = {}
        for d, m in candidate:
            ora = f' {m["time"]}' if m.get("time") else ""
            per_etichetta[f'{m["team1"]} vs {m["team2"]} — {d}{ora}'] = m
        scelta = st.selectbox(
            "⚽ Seleziona la partita",
            list(per_etichetta.keys()),
            key=f"quote_partita_{torneo_corrente()}_{stagione_corrente()}",
        )
        m_sel = per_etichetta[scelta]
        casa, ospite = m_sel["team1"], m_sel["team2"]
        solo_it = st.checkbox(
            "Solo bookmaker italiani (ADM)", value=True, key=f"q_solo_it_{torneo_corrente()}"
        )
        if st.session_state.get("quote_msg"):
            st.success(st.session_state.quote_msg)
            st.session_state.quote_msg = None

        cat, evento, avviso, records = ottieni_catalogo_partita(casa, ospite, solo_it)

        with st.expander("🔧 Diagnostica API"):
            if ODDS_API_KEY:
                lista = carica_quote_api(ODDS_API_KEY)
                st.write(f"Eventi ricevuti: **{len(lista['odds'])}**" if lista["ok"] else lista["errore"])
            righe_mk = {}
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                kk = (str(rec.get("market", "")), str(rec.get("line", "")),
                      str(rec.get("scope", "")), str(rec.get("period", "")))
                r = righe_mk.setdefault(kk, {"Mercato": kk[0], "Linea": kk[1], "Scope": kk[2],
                                             "Periodo": kk[3], "Bookmaker": 0, "Esiti": set()})
                r["Bookmaker"] = max(r["Bookmaker"], len(rec.get("bookmakers") or []))
                for bm in rec.get("bookmakers") or []:
                    r["Esiti"].update((bm.get("outcomes") or {}).keys())
            if righe_mk:
                st.write("Mercati ricevuti per questa partita:")
                st.dataframe(
                    pd.DataFrame(
                        [{**r, "Esiti": ", ".join(sorted(map(str, r["Esiti"])))[:80]}
                         for r in righe_mk.values()]
                    ),
                    use_container_width=True, hide_index=True,
                )

        if not cat:
            st.warning(avviso or "⚠️ Nessuna quota disponibile per questa partita.")
            return
        if avviso:
            st.info(avviso)
        st.caption(f"Evento trovato: {evento.get('home_team')} vs {evento.get('away_team')}")

        mercati = [x for x in ORDINE_MERCATI if x in cat]
        mercato = st.selectbox("Mercato", mercati, key=f"q_mercato_{torneo_corrente()}")
        giocate = sorted(cat[mercato].keys(), key=lambda g: _ordine_giocata(mercato, g))
        righe = []
        for g in giocate:
            pb = cat[mercato][g]
            best_b, best_q = max(pb.items(), key=lambda x: x[1])
            righe.append({
                "Giocata": g,
                "Miglior quota": round(best_q, 2),
                "Bookmaker": best_b,
                "Quota media": round(sum(pb.values()) / len(pb), 2),
                "N. book": len(pb),
            })
        st.markdown("### 📊 Confronto quote")
        st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)

        if len(giocate) <= 8:
            with st.expander("Quote per bookmaker"):
                books = sorted({b for g in giocate for b in cat[mercato][g]})
                st.dataframe(
                    pd.DataFrame([
                        {"Bookmaker": b, **{g: cat[mercato][g].get(b) for g in giocate}}
                        for b in books
                    ]),
                    use_container_width=True, hide_index=True,
                )

        st.markdown("**➕ Aggiungi alla schedina (miglior quota)**")
        mk = _chiave_testo(mercato)
        g_add = st.selectbox("Giocata", giocate, key=f"q_add_{mk}")
        best_b, best_q = max(cat[mercato][g_add].items(), key=lambda x: x[1])
        if st.button(
            f"➕ {g_add} @ {best_q:.2f} ({best_b})",
            key=f"q_btn_add_{mk}_{_chiave_testo(g_add)}",
            use_container_width=True,
        ):
            aggiungi_alla_schedina(
                f'{casa} - {ospite} ({str(m_sel.get("date", ""))[:10]})',
                etichetta_slip(mercato, g_add), best_q, "quote_msg",
            )
        st.caption("Le quote cambiano: verificale sempre sul sito dell'operatore.")


PARTIZIONI = [
    ("Esito finale 1X2", ["1", "X", "2"]),
    ("Under/Over", ["Over 2.5", "Under 2.5"]),
    ("Goal/No Goal", ["Goal", "No Goal"]),
]


def prob_mercato(cat, mercato, giocate):
    """Probabilità del mercato senza margine, mediate tra i bookmaker.

    Per ogni bookmaker: 1/quota di ogni esito, poi si divide per la somma
    (così il margine sparisce). Ritorna ({giocata: %}, margine medio %, n. bookmaker)
    oppure None se mancano i dati.
    """
    tabella = (cat or {}).get(mercato)
    if not tabella or any(g not in tabella for g in giocate):
        return None
    books = set(tabella[giocate[0]])
    for g in giocate[1:]:
        books &= set(tabella[g])
    if not books:
        return None
    acc = {g: [] for g in giocate}
    margini = []
    for b in books:
        inv = {g: 1.0 / tabella[g][b] for g in giocate}
        tot = sum(inv.values())
        margini.append((tot - 1) * 100)
        for g in giocate:
            acc[g].append(inv[g] / tot * 100)
    probs = {g: sum(v) / len(v) for g, v in acc.items()}
    return probs, sum(margini) / len(margini), len(books)


def catalogo_da_evento(evento, solo_italia=True):
    """Catalogo delle quote 1X2 contenute nell'evento (nessuna richiesta all'API)."""
    cat = costruisci_catalogo([evento], solo_italia)
    if not cat and solo_italia:
        cat = costruisci_catalogo([evento], False)
    return cat


def indice_eventi_quote(odds_list):
    """Indice veloce (squadra casa, squadra ospite) -> evento, per molte partite insieme."""
    idx = {}
    for ev in odds_list or []:
        if isinstance(ev, dict):
            idx[(_canon_squadra(ev.get("home_team", "")), _canon_squadra(ev.get("away_team", "")))] = ev
    return idx


def evento_da_indice(idx, casa, ospite, soglia=0.8):
    c1, c2 = _canon_squadra(casa), _canon_squadra(ospite)
    ev = idx.get((c1, c2))
    if ev is not None:
        return ev

    def sim(x, y):
        return 1.0 if x == y else difflib.SequenceMatcher(None, x, y).ratio()

    migliore, punteggio = None, 0.0
    for (h, a), e in idx.items():
        if h[:3] != c1[:3] and a[:3] != c2[:3]:
            continue
        sc = min(sim(c1, h), sim(c2, a))
        if sc > punteggio:
            migliore, punteggio = e, sc
    return migliore if punteggio >= soglia else None


def mostra_quote_confronto(t1, t2, dettagli):
    st.markdown("### 💰 Modello vs mercato")
    if not ODDS_API_KEY:
        st.info("Chiave ODDS_API_KEY non configurata: quote non disponibili.")
        return
    try:
        res = carica_quote_api(ODDS_API_KEY)
        if not res["ok"]:
            st.info(f"Quote non disponibili: {res['errore']}")
            return
        evento, _ = trova_evento_quote(res["odds"], t1, t2)
        if evento is None:
            st.info(
                "Quote non trovate per questa partita: di solito sono "
                "disponibili solo per le gare dei prossimi giorni."
            )
            return

        chiave = f"cmp_{_chiave_testo(t1)}_{_chiave_testo(t2)}"
        solo_it = st.checkbox("Solo bookmaker italiani (ADM)", value=True, key=chiave + "_it")
        esteso = st.checkbox(
            "Includi anche Under/Over 2.5 e Goal (usa una richiesta in più all'API)",
            value=False, key=chiave + "_ext",
        )
        cat = catalogo_da_evento(evento, solo_it)
        if esteso:
            cat_tutti, _ev, avviso, _rec = ottieni_catalogo_partita(t1, t2, solo_it)
            if cat_tutti:
                cat = cat_tutti
            if avviso:
                st.info(avviso)

        e = dettagli.get("e", {}) if dettagli else {}
        modello = {
            "1": e.get("1"), "X": e.get("X"), "2": e.get("2"),
            "Over 2.5": e.get("over25"), "Under 2.5": e.get("under25"),
            "Goal": e.get("goal"), "No Goal": e.get("nogoal"),
        }
        nomi = {"1": f"1 - {t1}", "X": "X - Pareggio", "2": f"2 - {t2}"}

        righe, margini = [], []
        for mercato, giocate in PARTIZIONI:
            pm = prob_mercato(cat, mercato, giocate)
            if not pm:
                continue
            probs, margine, n = pm
            margini.append(f"{mercato}: {margine:.1f}% ({n} bookmaker)")
            for g in giocate:
                mkt, mod = probs[g], modello.get(g)
                diff = None if mod is None else mod - mkt
                if diff is None:
                    segnale = ""
                elif diff >= 5:
                    segnale = "▲ modello più alto"
                elif diff <= -5:
                    segnale = "▼ mercato più alto"
                else:
                    segnale = "in linea"
                righe.append({
                    "Esito": nomi.get(g, g),
                    "Modello %": None if mod is None else round(mod, 1),
                    "Mercato %": round(mkt, 1),
                    "Scarto": None if diff is None else round(diff, 1),
                    "Segnale": segnale,
                    "Miglior quota": round(max(cat[mercato][g].values()), 2),
                })
        if not righe:
            st.info("Nessuna quota 1X2 disponibile per questa partita.")
            return

        st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)

        if all(r["Modello %"] is not None for r in righe[:3]) and len(righe) >= 3:
            st.bar_chart(
                pd.DataFrame(
                    {"Modello": [r["Modello %"] for r in righe[:3]],
                     "Mercato": [r["Mercato %"] for r in righe[:3]]},
                    index=["1", "X", "2"],
                )
            )

        con_scarto = [r for r in righe if r["Scarto"] is not None]
        if con_scarto:
            top = max(con_scarto, key=lambda r: abs(r["Scarto"]))
            st.info(
                f"Scarto più grande: **{top['Esito']}**, modello {top['Modello %']}% "
                f"contro mercato {top['Mercato %']}% ({top['Scarto']:+.1f} punti). "
                "Il mercato conosce formazioni e infortuni che il modello non vede: "
                "uno scarto grande è un motivo per controllare, non per fidarsi del modello."
            )
        st.caption(
            "Mercato % = probabilità ricavata dalle quote dopo aver tolto il margine "
            "dei bookmaker, media tra i bookmaker. Scarto = modello meno mercato, in "
            "punti percentuali. Margine medio: " + "; ".join(margini) + ". "
            "Sono stime, non garanzie."
        )

        righe_book = []
        for book in evento.get("bookmakers", []):
            out = book.get("outcomes", {}) if isinstance(book, dict) else {}
            righe_book.append({
                "Bookmaker": book.get("key", "N/D"),
                "1": _quota(out.get("HOME")),
                "X": _quota(out.get("DRAW")),
                "2": _quota(out.get("AWAY")),
            })
        if righe_book:
            with st.expander(f"Quote 1X2 per bookmaker ({len(righe_book)})"):
                st.dataframe(pd.DataFrame(righe_book), use_container_width=True, hide_index=True)
    except Exception as ex:
        st.info(f"Quote non disponibili: {ex}")


def mostra_stato_quote():
    test_odds = testa_odds_api()
    if test_odds["ok"]:
        st.success("🟢 Collegamento quote prepartita: OK")
    else:
        st.error(f"🔴 Collegamento quote prepartita: {test_odds['errore']}")
    st.markdown("<p style='text-align: center; color: #8b949e; font-style: italic; font-size: 11px; margin-top: -10px; margin-bottom: 15px; letter-spacing: 1px;'>The bible of analysis</p>", unsafe_allow_html=True)
        
