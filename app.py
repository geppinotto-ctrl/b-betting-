from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components
import pandas as pd
import requests
import streamlit as st

try:
    from zoneinfo import ZoneInfo

    TZ_ITALIA = ZoneInfo("Europe/Rome")
except Exception:
    TZ_ITALIA = timezone(timedelta(hours=2))

st.set_page_config(
    page_title="b-betting — Live Dashboard", page_icon="⚽", layout="wide"
)

st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    .stTextInput > div > div > input { background-color: #161b22; color: #c9d1d9; border-radius: 8px; border: 1px solid #30363d; }
    .league-section { color: #8b949e; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; }
    .ai-box { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; margin-top: 15px; margin-bottom: 15px; color: #c9d1d9; font-size: 14px; }
    .smart-tip-box { background-color: #111b27; border: 1px solid #1f6feb; padding: 20px; border-radius: 12px; margin-top: 20px; margin-bottom: 20px; color: #c9d1d9; }
    .timer-box { background-color: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 15px; color: #58a6ff; font-weight: bold; font-size: 13px; }

    .badge-v { background-color: #238636; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }
    .badge-n { background-color: #d29922; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }
    .badge-p { background-color: #da3633; color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold; margin-right: 4px; display: inline-block; }

    .stTabs [data-baseweb="tab-list"] button:nth-child(1) {
        background-color: rgba(35, 134, 54, 0.15);
        border: 1px solid #238636;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(1):hover {
        background-color: rgba(35, 134, 54, 0.3);
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(2) {
        background-color: rgba(210, 153, 34, 0.15);
        border: 1px solid #d29922;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(2):hover {
        background-color: rgba(210, 153, 34, 0.3);
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(3) {
        background-color: rgba(218, 54, 51, 0.15);
        border: 1px solid #da3633;
        border-radius: 8px 8px 0 0;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(3):hover {
        background-color: rgba(218, 54, 51, 0.3);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "pagina" not in st.session_state:
    st.session_state.pagina = "home"

campionati_disponibili = [
    "Italia - Serie A",
    "Inghilterra - Premier League",
    "Spagna - La Liga",
    "Germania - Bundesliga",
    "Francia - Ligue 1",
    "UEFA Champions League",
]

mapping_file_torneo = {
    "Italia - Serie A": ["it.1.json", "italy/it.1.json"],
    "Inghilterra - Premier League": ["en.1.json", "england/en.1.json"],
    "Spagna - La Liga": ["es.1.json", "spain/es.1.json"],
    "Germania - Bundesliga": ["de.1.json", "germany/de.1.json"],
    "Francia - Ligue 1": ["fr.1.json", "france/fr.1.json"],
    "UEFA Champions League": ["cl.json", "champions-league/index.json"],
}

now = datetime.now(TZ_ITALIA)

with st.sidebar:
    st.header("Selettore Tornei")

    giorni_it = [
        "Lunedì",
        "Martedì",
        "Mercoledì",
        "Giovedì",
        "Venerdì",
        "Sabato",
        "Domenica",
    ]
    components.html(
        """
        <div style="background:#161b22;border:1px solid #30363d;padding:10px;border-radius:8px;text-align:center;color:#58a6ff;font-family:sans-serif;font-weight:bold;font-size:13px;">
            🕒 Orologio Live (Italia)<br>
            <span id="orologio" style="font-size:16px;"></span>
        </div>
        <script>
        function aggiorna() {
            const opt = {timeZone: 'Europe/Rome', weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false};
            document.getElementById('orologio').textContent = new Intl.DateTimeFormat('it-IT', opt).format(new Date());
        }
        aggiorna();
        setInterval(aggiorna, 1000);
        </script>
        """,
        height=80,
    )

    stagione_selezionata = st.selectbox(
        "Stagione", ["2026-27", "2025-26", "2024-25"]
    )
    campionato_top = st.selectbox("Torneo", campionati_disponibili)

    st.divider()
    if st.button("🏠 Torna alla Home", use_container_width=True):
        st.session_state.pagina = "home"
        st.rerun()

    if st.button("🔄 Aggiorna Dati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
@st.cache_data
def carica_dati_campionato(nome_campionato, stagione):
    possibili_nomi = mapping_file_torneo.get(nome_campionato, ["it.1.json"])
    anno_inizio = stagione.split("-")[0]
    percorsi_da_tentare = []
    for nome_file in possibili_nomi:
        percorsi_da_tentare.append(f"{stagione}/{nome_file}")
        percorsi_da_tentare.append(nome_file)
        percorsi_da_tentare.append(f"{anno_inizio}/{nome_file}")

    for p in percorsi_da_tentare:
        url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{p}"
        try:
            r = requests.get(url, timeout=4)
            if r.status_code == 200:
                res = r.json()
                if isinstance(res, list):
                    return {"matches": res}
                if isinstance(res, dict):
                    if "matches" in res:
                        return res
                    for v in res.values():
                        if isinstance(v, list):
                            return {"matches": v}
        except Exception:
            pass

    return {"matches": []}


def calcola_statistiche_squadra(matches, squadra):
    match_squadra = [
        m
        for m in matches
        if isinstance(m, dict)
        and isinstance(m.get("score"), dict)
        and m["score"].get("ft") is not None
        and (m.get("team1") == squadra or m.get("team2") == squadra)
    ]

    tot = len(match_squadra)
    if tot == 0:
        return None

    gf, gs, pt = 0, 0, 0
    clean_sheets = 0
    over_2_5 = 0
    btts = 0
    forma = []

    for m in match_squadra:
        is_casa = m.get("team1") == squadra
        ft = m["score"]["ft"]
        g1, g2 = ft[0], ft[1]
        m_gf = g1 if is_casa else g2
        m_gs = g2 if is_casa else g1

        gf += m_gf
        gs += m_gs

        if m_gs == 0:
            clean_sheets += 1
        if (g1 + g2) > 2.5:
            over_2_5 += 1
        if g1 > 0 and g2 > 0:
            btts += 1

        if m_gf > m_gs:
            forma.append("V")
            pt += 3
        elif m_gf == m_gs:
            forma.append("N")
            pt += 1
        else:
            forma.append("P")

    return {
        "tot": tot,
        "forma": forma,
        "ppg": round(pt / tot, 2),
        "gf_avg": round(gf / tot, 2),
        "gs_avg": round(gs / tot, 2),
        "clean_sheets_pct": round((clean_sheets / tot) * 100, 1),
        "over_2_5_pct": round((over_2_5 / tot) * 100, 1),
        "btts_pct": round((btts / tot) * 100, 1),
    }


def calcola_pronostico_ia(stats1, stats2):
    if not stats1 or not stats2:
        return 33.3, 33.4, 33.3

    forza_1 = stats1["ppg"] * 1.5 + (stats1["gf_avg"] - stats1["gs_avg"]) * 0.5
    forza_2 = stats2["ppg"] * 1.5 + (stats2["gf_avg"] - stats2["gs_avg"]) * 0.5
    forza_1 += 0.2  # vantaggio campo

    diff = forza_1 - forza_2

    base_1 = 40 + (diff * 18)
    base_2 = 40 - (diff * 18)
    base_x = 26 - abs(diff * 5)

    p1 = max(10.0, min(80.0, base_1))
    p2 = max(10.0, min(80.0, base_2))
    px = max(10.0, min(50.0, base_x))

    tot_p = p1 + px + p2
    return (
        round((p1 / tot_p) * 100, 1),
        round((px / tot_p) * 100, 1),
        round((p2 / tot_p) * 100, 1),
    )


def genera_analisi_ia_match(t1, t2, p1, px, p2):
    favorevole = t1 if p1 > p2 else (t2 if p2 > p1 else "Equilibrio")
    righe = [
        f"🤖 <b>Report e Pronostico IA — {t1} vs {t2}</b><br><br>",
        f"• <b>Predizione Esito Finale (1X2):</b> {p1}% per la vittoria di {t1} (1), "
        f"{px}% per il pareggio (X), {p2}% per il successo di {t2} (2).<br>",
        f"• <b>Tendenza:</b> vantaggio potenziale per <b>{favorevole}</b> "
        "in base ai punti a partita (PPG) e alla solidità difensiva.<br>",
        "• <b>Consiglio:</b> valutare coperture o mercati combinati "
        "(es. 1X o Goal) se il pareggio supera il 25%.",
    ]
    return "".join(righe)


def mostra_metriche_squadra(titolo, stats):
    st.markdown(titolo, unsafe_allow_html=True)
    if stats:
        st.metric("Punti a Partita (PPG)", stats["ppg"])
        st.metric("Media Gol Fatti", stats["gf_avg"])
        st.metric("Media Gol Subiti", stats["gs_avg"])
        st.metric("Over 2.5 %", f"{stats['over_2_5_pct']}%")
        st.metric("Clean Sheet %", f"{stats['clean_sheets_pct']}%")
        st.metric("BTTS %", f"{stats['btts_pct']}%")
    else:
        st.info("Dati insufficienti per questa squadra.")
def trova_scontri_diretti(campionato, t1, t2, max_scontri=5):
    stagioni = ["2026-27", "2025-26", "2024-25"]
    trovati = []
    for stag in stagioni:
        dati = carica_dati_campionato(campionato, stag)
        for m in dati.get("matches", []):
            if not isinstance(m, dict):
                continue
            s = m.get("score")
            if not isinstance(s, dict) or not s.get("ft"):
                continue
            a, b = m.get("team1"), m.get("team2")
            if {a, b} == {t1, t2}:
                trovati.append(
                    (str(m.get("date", "")), a, b, s["ft"][0], s["ft"][1])
                )
    trovati.sort(reverse=True)
    return trovati[:max_scontri]


def mostra_scontri_diretti(campionato, t1, t2):
    st.markdown("#### 🤝 Ultimi scontri diretti")
    scontri = trova_scontri_diretti(campionato, t1, t2)
    if not scontri:
        st.info("Nessuno scontro diretto trovato nelle ultime stagioni.")
        return

    v1, v2, pa = 0, 0, 0
    righe = []
    for data, casa, osp, g1, g2 in scontri:
        if g1 == g2:
            pa += 1
        elif (g1 > g2 and casa == t1) or (g2 > g1 and osp == t1):
            v1 += 1
        else:
            v2 += 1
        righe.append({"Data": data, "Partita": f"{casa} {g1}-{g2} {osp}"})

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Vittorie {t1}", v1)
    c2.metric("Pareggi", pa)
    c3.metric(f"Vittorie {t2}", v2)
    st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)
def mostra_grafico_forma(dati, n=10):
    st.markdown(f"#### 📈 Andamento punti (ultime {n} partite)")
    valori = {"V": 3, "N": 1, "P": 0}
    serie = {}
    for nome, stats in dati.items():
        if stats and stats["forma"]:
            totale = 0
            cumulati = []
            for r in stats["forma"][-n:]:
                totale += valori[r]
                cumulati.append(totale)
            serie[nome] = cumulati

    if not serie:
        st.info("Dati insufficienti per il grafico.")
        return

    df = pd.DataFrame({k: pd.Series(v) for k, v in serie.items()})
    df.index = range(1, len(df) + 1)
    df.index.name = "Partita"
    st.line_chart(df)
def _hash_nome(nome):
    import zlib

    return zlib.crc32(str(nome).encode("utf-8"))


def iniziali_squadra(nome):
    ignora = {"FC", "AC", "AS", "SS", "US", "CF", "SC", "RC", "SV", "AFC",
              "CD", "UD", "SD", "VFB", "VFL", "DE", "DI"}
    parole = [
        p for p in str(nome).replace(".", " ").split()
        if p.upper() not in ignora and not any(c.isdigit() for c in p)
    ]
    if not parole:
        return str(nome)[:3].upper()
    if len(parole) == 1:
        return parole[0][:3].upper()
    return (parole[0][0] + parole[1][0]).upper()


def badge_squadra(nome):
    tinta = _hash_nome(nome) % 360
    return (
        f"<span style='background:hsl({tinta}, 65%, 42%);color:white;"
        "padding:3px 7px;border-radius:12px;font-size:11px;font-weight:bold;"
        "display:inline-block;min-width:34px;text-align:center;margin-right:6px;'>"
        f"{iniziali_squadra(nome)}</span>"
    )


def simbolo_squadra(nome):
    cerchi = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫"]
    return cerchi[_hash_nome(nome) % len(cerchi)]
def calcola_stats_tempi(matches, squadra):
    gf1 = gs1 = gf2 = gs2 = 0
    segna_1t = 0
    tot = 0
    for m in matches:
        if not isinstance(m, dict):
            continue
        s = m.get("score")
        if not isinstance(s, dict):
            continue
        ft, ht = s.get("ft"), s.get("ht")
        if not ft or not ht:
            continue
        if squadra not in (m.get("team1"), m.get("team2")):
            continue
        casa = m.get("team1") == squadra
        f_fatti, f_subiti = (ft[0], ft[1]) if casa else (ft[1], ft[0])
        h_fatti, h_subiti = (ht[0], ht[1]) if casa else (ht[1], ht[0])
        gf1 += h_fatti
        gs1 += h_subiti
        gf2 += f_fatti - h_fatti
        gs2 += f_subiti - h_subiti
        if h_fatti > 0:
            segna_1t += 1
        tot += 1

    if tot == 0:
        return None
    return {
        "tot": tot,
        "gf1": round(gf1 / tot, 2),
        "gs1": round(gs1 / tot, 2),
        "gf2": round(gf2 / tot, 2),
        "gs2": round(gs2 / tot, 2),
        "segna_1t_pct": round(segna_1t / tot * 100, 1),
    }


def mostra_stats_tempi(titolo, stats):
    st.markdown(titolo)
    if not stats:
        st.info("Dati del primo tempo non disponibili.")
        return
    df = pd.DataFrame(
        {
            "Tempo": ["1° tempo", "2° tempo"],
            "Fatti (media)": [stats["gf1"], stats["gf2"]],
            "Subiti (media)": [stats["gs1"], stats["gs2"]],
        }
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.metric("Segna nel 1° tempo", f"{stats['segna_1t_pct']}%")
    st.caption(f"Calcolato su {stats['tot']} partite con dato del primo tempo.")
    
import difflib
import io
import re

CODICI_FD = {
    "Italia - Serie A": "I1",
    "Inghilterra - Premier League": "E0",
    "Spagna - La Liga": "SP1",
    "Germania - Bundesliga": "D1",
    "Francia - Ligue 1": "F1",
}


@st.cache_data(ttl=3600)
def carica_stats_extra(campionato, stagione):
    codice = CODICI_FD.get(campionato)
    if not codice:
        return None
    anno_a = stagione.split("-")[0][2:]
    anno_b = stagione.split("-")[1]
    url = f"https://www.football-data.co.uk/mmz4281/{anno_a}{anno_b}/{codice}.csv"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return None
        df = pd.read_csv(
            io.BytesIO(r.content), encoding="latin-1", on_bad_lines="skip"
        )
        df = df.dropna(subset=["HomeTeam", "AwayTeam"])
        return df if not df.empty else None
    except Exception:
        return None


def normalizza_nome(nome):
    n = re.sub(r"[^a-z ]", " ", str(nome).lower())
    togli = {"fc", "ac", "as", "ss", "ssc", "us", "acf", "afc", "cfc", "bc",
             "calcio", "hellas", "club", "de", "di"}
    return " ".join(p for p in n.split() if p not in togli)


def trova_nome_fd(nome, nomi_fd):
    n = normalizza_nome(nome)
    if not n:
        return None
    mappa = {normalizza_nome(x): x for x in nomi_fd}
    if n in mappa:
        return mappa[n]
    for k, v in mappa.items():
        if k and (n.startswith(k) or k.startswith(n)):
            return v
    simili = difflib.get_close_matches(n, list(mappa.keys()), n=1, cutoff=0.8)
    return mappa[simili[0]] if simili else None


def calcola_stats_extra(df, nome):
    nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
    nome_fd = trova_nome_fd(nome, nomi)
    if not nome_fd:
        return None
    casa = df[df["HomeTeam"] == nome_fd]
    fuori = df[df["AwayTeam"] == nome_fd]
    tot = len(casa) + len(fuori)
    if tot == 0:
        return None

    def media(col_casa, col_fuori):
        if col_casa not in df.columns or col_fuori not in df.columns:
            return None
        v = (
            pd.to_numeric(casa[col_casa], errors="coerce").dropna().tolist()
            + pd.to_numeric(fuori[col_fuori], errors="coerce").dropna().tolist()
        )
        return round(sum(v) / len(v), 2) if v else None

    return {
        "nome_fd": nome_fd,
        "tot": tot,
        "angoli_f": media("HC", "AC"),
        "angoli_s": media("AC", "HC"),
        "tiri_f": media("HS", "AS"),
        "tiri_s": media("AS", "HS"),
        "porta_f": media("HST", "AST"),
        "porta_s": media("AST", "HST"),
        "falli": media("HF", "AF"),
        "gialli": media("HY", "AY"),
        "rossi": media("HR", "AR"),
    }


def mostra_stats_extra(titolo, nome):
    st.markdown(titolo)
    df = carica_stats_extra(campionato_top, stagione_selezionata)
    if df is None:
        st.info(
            "Statistiche aggiuntive disponibili solo per la Serie A "
            "e se la stagione ha i dati."
        )
        return
    stats = calcola_stats_extra(df, nome)
    if not stats:
        st.warning(f"Squadra '{nome}' non riconosciuta nei dati aggiuntivi.")
        return

    def v(x):
        return "-" if x is None else str(x)

    tabella = pd.DataFrame(
        [
            {"Statistica": "Calci d'angolo", "Fatti": v(stats["angoli_f"]), "Subiti": v(stats["angoli_s"])},
            {"Statistica": "Tiri", "Fatti": v(stats["tiri_f"]), "Subiti": v(stats["tiri_s"])},
            {"Statistica": "Tiri in porta", "Fatti": v(stats["porta_f"]), "Subiti": v(stats["porta_s"])},
            {"Statistica": "Falli commessi", "Fatti": v(stats["falli"]), "Subiti": "-"},
            {"Statistica": "Cartellini gialli", "Fatti": v(stats["gialli"]), "Subiti": "-"},
            {"Statistica": "Cartellini rossi", "Fatti": v(stats["rossi"]), "Subiti": "-"},
        ]
    )
    st.dataframe(tabella, use_container_width=True, hide_index=True)
    st.caption(
        f"Media su {stats['tot']} partite. Fonte: football-data.co.uk "
        f"(nome nei dati: {stats['nome_fd']})."
        )
import math


def _poisson(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def calcola_forze(matches, d=0.95, prior=4):
    gio = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        s = m.get("score")
        ft = s.get("ft") if isinstance(s, dict) else None
        if ft and m.get("team1") and m.get("team2"):
            gio.append((m["team1"], m["team2"], ft[0], ft[1]))
    if len(gio) < 10:
        return None
    n = len(gio)
    mc = sum(g[2] for g in gio) / n
    mf = sum(g[3] for g in gio) / n
    media_sq = (mc + mf) / 2
    storico = {}
    for t1, t2, a, b in gio:
        storico.setdefault(t1, []).append((a, b))
        storico.setdefault(t2, []).append((b, a))
    forze = {}
    for t, lista in storico.items():
        k = len(lista)
        pesi = [d ** (k - 1 - i) for i in range(k)]
        sp = sum(pesi)
        gf = sum(p * x[0] for p, x in zip(pesi, lista))
        gs = sum(p * x[1] for p, x in zip(pesi, lista))
        forze[t] = {
            "att": (gf + prior * media_sq) / (sp + prior) / media_sq,
            "dif": (gs + prior * media_sq) / (sp + prior) / media_sq,
        }
    return {"mc": mc, "mf": mf, "forze": forze}


def forze_tiri(df):
    if df is None or "HST" not in df.columns or "AST" not in df.columns:
        return None
    d = df.dropna(subset=["HomeTeam", "AwayTeam"]).copy()
    d["HST"] = pd.to_numeric(d["HST"], errors="coerce")
    d["AST"] = pd.to_numeric(d["AST"], errors="coerce")
    d = d.dropna(subset=["HST", "AST"])
    if len(d) < 10:
        return None
    media = (d["HST"].mean() + d["AST"].mean()) / 2
    out = {}
    for s in set(d["HomeTeam"]) | set(d["AwayTeam"]):
        c = d[d["HomeTeam"] == s]
        f = d[d["AwayTeam"] == s]
        fatti = list(c["HST"]) + list(f["AST"])
        subiti = list(c["AST"]) + list(f["HST"])
        k = len(fatti)
        out[s] = {
            "att": (sum(fatti) + 4 * media) / (k + 4) / media,
            "dif": (sum(subiti) + 4 * media) / (k + 4) / media,
        }
    return out


def gol_attesi(modello, t1, t2, tiri=None, nome_fd1=None, nome_fd2=None, peso_tiri=0.3):
    f = modello["forze"]
    l1 = modello["mc"] * f[t1]["att"] * f[t2]["dif"]
    l2 = modello["mf"] * f[t2]["att"] * f[t1]["dif"]
    usato = False
    if tiri and nome_fd1 in tiri and nome_fd2 in tiri:
        s1 = modello["mc"] * tiri[nome_fd1]["att"] * tiri[nome_fd2]["dif"]
        s2 = modello["mf"] * tiri[nome_fd2]["att"] * tiri[nome_fd1]["dif"]
        l1 = (1 - peso_tiri) * l1 + peso_tiri * s1
        l2 = (1 - peso_tiri) * l2 + peso_tiri * s2
        usato = True
    return l1, l2, usato


def esiti_poisson(l1, l2, max_gol=8):
    p1 = [_poisson(i, l1) for i in range(max_gol + 1)]
    p2 = [_poisson(i, l2) for i in range(max_gol + 1)]
    tot = sum(p1) * sum(p2)
    vit1 = pareggio = vit2 = over25 = btts = 0.0
    risultati = []
    for i in range(max_gol + 1):
        for j in range(max_gol + 1):
            p = p1[i] * p2[j] / tot
            risultati.append((f"{i}-{j}", p))
            if i > j:
                vit1 += p
            elif i == j:
                pareggio += p
            else:
                vit2 += p
            if i + j > 2:
                over25 += p
            if i > 0 and j > 0:
                btts += p
    risultati.sort(key=lambda x: x[1], reverse=True)
    return {
        "1": vit1 * 100,
        "X": pareggio * 100,
        "2": vit2 * 100,
        "over25": over25 * 100,
        "under25": (1 - over25) * 100,
        "goal": btts * 100,
        "nogoal": (1 - btts) * 100,
        "top": risultati[:5],
    }

def mostra_dna_pronostico(t1, t2, dettagli):
    if not dettagli:
        st.info("🧬 DNA del pronostico non disponibile.")
        return

    l1 = dettagli.get("l1")
    l2 = dettagli.get("l2")
    e = dettagli.get("e", {})
    usato_tiri = dettagli.get("tiri", False)

    st.markdown("### 🧬 DNA DEL PRONOSTICO")

    st.metric(f"⚽ Gol attesi — {t1}", f"{l1:.2f}")
    st.metric(f"⚽ Gol attesi — {t2}", f"{l2:.2f}")

    st.markdown("#### 📊 Esiti elaborati")

    st.metric("1 — Casa", f"{e.get('1', 0):.1f}%")
    st.metric("X — Pareggio", f"{e.get('X', 0):.1f}%")
    st.metric("2 — Trasferta", f"{e.get('2', 0):.1f}%")

    if usato_tiri:
        st.success("🎯 Modulo tiri integrato — peso 30%")
    else:
        st.info("🎯 Modulo tiri non disponibile — modello basato sui gol")

    top = e.get("top", [])

    if top:
        st.markdown("#### 🎯 Risultati esatti più probabili")

        dati_top = []

        for risultato, probabilita in top:
            dati_top.append({
                "Risultato": risultato,
                "Probabilità": f"{probabilita * 100:.2f}%"
            })

        st.dataframe(
            pd.DataFrame(dati_top),
            hide_index=True,
            use_container_width=True
        )
def mostra_pronostico_v2(matches, t1, t2):
    st.markdown("### 🧠 Pronostico v2 (modello di Poisson)")
    modello = calcola_forze(matches)
    if not modello or t1 not in modello["forze"] or t2 not in modello["forze"]:
        st.info("Servono più partite giocate per stimare il modello.")
        return

    df = carica_stats_extra(campionato_top, stagione_selezionata)
    tiri = forze_tiri(df)
    nome1 = nome2 = None
    if tiri is not None and df is not None:
        nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
        nome1 = trova_nome_fd(t1, nomi)
        nome2 = trova_nome_fd(t2, nomi)

    l1, l2, usato_tiri = gol_attesi(modello, t1, t2, tiri, nome1, nome2)
    e = esiti_poisson(l1, l2)

    def riga(nome, p):
        quota = f"{100 / p:.2f}" if p > 0.1 else "-"
        return {"Mercato": nome, "Probabilità": f"{p:.1f}%", "Quota equa": quota}

    tabella = pd.DataFrame(
        [
            riga(f"1 - {t1}", e["1"]),
            riga("X - Pareggio", e["X"]),
            riga(f"2 - {t2}", e["2"]),
            riga("Over 2.5", e["over25"]),
            riga("Under 2.5", e["under25"]),
            riga("Goal (segnano entrambe)", e["goal"]),
            riga("NoGoal", e["nogoal"]),
        ]
    )
    st.dataframe(tabella, use_container_width=True, hide_index=True)

    st.markdown("**Risultati esatti più probabili**")
    top = pd.DataFrame(
        [{"Risultato": r, "Probabilità": f"{p * 100:.1f}%"} for r, p in e["top"]]
    )
    st.dataframe(top, use_container_width=True, hide_index=True)

    base = "con tiri in porta (peso 30%)" if usato_tiri else "solo sui gol"
    st.caption(
        f"Gol attesi: {t1} {l1:.2f} - {t2} {l2:.2f}. Calcolo {base}, "
        "con più peso alle partite recenti. La quota equa è 100 diviso la "
        "probabilità, cioè senza il margine del bookmaker. È una stima, "
        "non una garanzia."
    )
def mostra_riepilogo(matches, tab):
    with tab:
        st.subheader("🎯 Riepilogo Pronostici")
        modello = calcola_forze(matches)
        if not modello:
            st.info("Servono più partite giocate per stimare il modello.")
            return

        oggi = now.strftime("%Y-%m-%d")
        c1, c2 = st.columns(2)
        with c1:
            giorni = st.selectbox(
                "Partite in arrivo",
                ["Prossimi 7 giorni", "Prossimi 14 giorni", "Prossimi 30 giorni", "Tutte"],
                index=1,
                key=f"riep_giorni_{campionato_top}_{stagione_selezionata}",
            )
        with c2:
            ordine = st.selectbox(
                "Ordina per",
                ["Probabilità più alta", "Data", "Over 2.5", "Goal"],
                key=f"riep_ordine_{campionato_top}_{stagione_selezionata}",
            )

        limite = None
        if giorni != "Tutte":
            n = int(giorni.split()[1])
            limite = (now + timedelta(days=n)).strftime("%Y-%m-%d")

        prossime = [
            m
            for m in matches
            if isinstance(m, dict)
            and m.get("team1")
            and m.get("team2")
            and not (isinstance(m.get("score"), dict) and m["score"].get("ft"))
            and str(m.get("date", "")) >= oggi
            and (limite is None or str(m.get("date", "")) <= limite)
        ]
        if not prossime:
            st.info("Nessuna partita in arrivo nel periodo scelto.")
            return

        df = carica_stats_extra(campionato_top, stagione_selezionata)
        tiri = forze_tiri(df)
        nomi = set()
        if tiri is not None and df is not None:
            nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
        cache_nomi = {}

        def nome_fd(t):
            if t not in cache_nomi:
                cache_nomi[t] = trova_nome_fd(t, nomi) if nomi else None
            return cache_nomi[t]

        righe = []
        for m in prossime:
            t1, t2 = m["team1"], m["team2"]
            if t1 not in modello["forze"] or t2 not in modello["forze"]:
                continue
            l1, l2, _ = gol_attesi(modello, t1, t2, tiri, nome_fd(t1), nome_fd(t2))
            e = esiti_poisson(l1, l2)
            esiti = {"1": e["1"], "X": e["X"], "2": e["2"]}
            migliore = max(esiti, key=esiti.get)
            p = esiti[migliore]
            righe.append(
                {
                    "Data": str(m.get("date", "")),
                    "Partita": f"{t1} - {t2}",
                    "Esito": migliore,
                    "Prob. esito": round(p, 1),
                    "Quota equa": round(100 / p, 2),
                    "1": round(e["1"], 1),
                    "X": round(e["X"], 1),
                    "2": round(e["2"], 1),
                    "Over 2.5": round(e["over25"], 1),
                    "Goal": round(e["goal"], 1),
                }
            )

        if not righe:
            st.info("Squadre non presenti nel modello.")
            return

        chiavi = {
            "Probabilità più alta": ("Prob. esito", True),
            "Data": ("Data", False),
            "Over 2.5": ("Over 2.5", True),
            "Goal": ("Goal", True),
        }
        colonna, decrescente = chiavi[ordine]
        righe.sort(key=lambda r: r[colonna], reverse=decrescente)

        st.dataframe(
            pd.DataFrame(righe),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Prob. esito": st.column_config.ProgressColumn(
                    "Prob. %", format="%.1f", min_value=0, max_value=100
                ),
            },
        )
        st.caption(
            f"{len(righe)} partite. Tocca l'intestazione di una colonna per "
            "riordinare. Probabilità in %, stime del modello di Poisson: "
            "non sono garanzie."
        )
def probabilita_v2(matches, t1, t2, stats1, stats2):
    modello = calcola_forze(matches)
    if modello and t1 in modello["forze"] and t2 in modello["forze"]:
        df = carica_stats_extra(campionato_top, stagione_selezionata)
        tiri = forze_tiri(df)
        nome1 = nome2 = None
        if tiri is not None and df is not None:
            nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
            nome1 = trova_nome_fd(t1, nomi)
            nome2 = trova_nome_fd(t2, nomi)
        l1, l2, usato_tiri = gol_attesi(modello, t1, t2, tiri, nome1, nome2)
        e = esiti_poisson(l1, l2)
        dettagli = {"l1": l1, "l2": l2, "e": e, "tiri": usato_tiri}
        return round(e["1"], 1), round(e["X"], 1), round(e["2"], 1), dettagli
    p1, px, p2 = calcola_pronostico_ia(stats1, stats2)
    return p1, px, p2, None


def genera_analisi_v2(t1, t2, p1, px, p2, dettagli):
    if not dettagli:
        return genera_analisi_ia_match(t1, t2, p1, px, p2)
    e = dettagli["e"]
    esiti = {
        f"vittoria di {t1} (1)": p1,
        "pareggio (X)": px,
        f"vittoria di {t2} (2)": p2,
    }
    migliore = max(esiti, key=esiti.get)
    pm = esiti[migliore]
    if pm < 40:
        tono = "partita molto equilibrata, nessun esito nettamente favorito"
    elif pm < 55:
        tono = "leggero vantaggio per questo esito"
    else:
        tono = "vantaggio netto per questo esito"
    risultato, rp = e["top"][0]
    base = "gol e tiri in porta" if dettagli["tiri"] else "gol"
    totale = dettagli["l1"] + dettagli["l2"]
    righe = [
        f"🤖 <b>Report IA v2 — {t1} vs {t2}</b><br><br>",
        f"• <b>Esito più probabile:</b> {migliore} al <b>{pm}%</b> ({tono}).<br>",
        f"• <b>Gol attesi:</b> {t1} {dettagli['l1']:.2f} - {t2} {dettagli['l2']:.2f} (totale {totale:.2f}).<br>",
        f"• <b>Mercati gol:</b> Over 2.5 al {e['over25']:.1f}%, Goal al {e['goal']:.1f}%.<br>",
        f"• <b>Risultato esatto più probabile:</b> {risultato} ({rp * 100:.1f}%).<br>",
        f"• <b>Base di calcolo:</b> {base}, con più peso alle partite recenti.",
    ]
    return "".join(righe)
def _giocate_ordinate(matches):
    gio = []
    for i, m in enumerate(matches):
        if not isinstance(m, dict):
            continue
        s = m.get("score")
        ft = s.get("ft") if isinstance(s, dict) else None
        if ft and m.get("team1") and m.get("team2"):
            gio.append((str(m.get("date", "")), i, m))
    gio.sort(key=lambda x: (x[0], x[1]))
    return [g[2] for g in gio]


@st.cache_data(ttl=3600, show_spinner=False)
def esegui_backtest(_matches, campionato, stagione, d, rodaggio):
    giocate = _giocate_ordinate(_matches)
    risultati = []
    c1 = cx = c2 = c_over = c_goal = 0
    for m in giocate[:rodaggio]:
        a, b = m["score"]["ft"][0], m["score"]["ft"][1]
        c1 += a > b
        cx += a == b
        c2 += a < b
        c_over += (a + b) > 2
        c_goal += (a > 0 and b > 0)
    for i in range(rodaggio, len(giocate)):
        m = giocate[i]
        a, b = m["score"]["ft"][0], m["score"]["ft"][1]
        modello = calcola_forze(giocate[:i], d=d)
        t1, t2 = m["team1"], m["team2"]
        if modello and t1 in modello["forze"] and t2 in modello["forze"]:
            l1, l2, _ = gol_attesi(modello, t1, t2)
            e = esiti_poisson(l1, l2)
            n = i
            risultati.append(
                {
                    "p": (e["1"] / 100, e["X"] / 100, e["2"] / 100),
                    "reale": 0 if a > b else (1 if a == b else 2),
                    "base": (c1 / n, cx / n, c2 / n),
                    "p_over": e["over25"] / 100,
                    "over": 1 if (a + b) > 2 else 0,
                    "base_over": c_over / n,
                    "p_goal": e["goal"] / 100,
                    "goal": 1 if (a > 0 and b > 0) else 0,
                    "base_goal": c_goal / n,
                }
            )
        c1 += a > b
        cx += a == b
        c2 += a < b
        c_over += (a + b) > 2
        c_goal += (a > 0 and b > 0)
    return risultati


def riassumi_backtest(ris):
    n = len(ris)
    if n < 10:
        return None
    acc = acc_base = brier = brier_base = 0.0
    acc_over = br_over = br_over_base = 0.0
    acc_goal = br_goal = br_goal_base = 0.0
    fasce = {"sotto 40%": [], "40-50%": [], "50-60%": [], "60% o più": []}
    for r in ris:
        p, base, reale = r["p"], r["base"], r["reale"]
        pred = max(range(3), key=lambda k: p[k])
        hit = 1 if pred == reale else 0
        acc += hit
        acc_base += 1 if max(range(3), key=lambda k: base[k]) == reale else 0
        brier += sum((p[k] - (1 if k == reale else 0)) ** 2 for k in range(3))
        brier_base += sum(
            (base[k] - (1 if k == reale else 0)) ** 2 for k in range(3)
        )
        acc_over += 1 if (r["p_over"] > 0.5) == (r["over"] == 1) else 0
        br_over += (r["p_over"] - r["over"]) ** 2
        br_over_base += (r["base_over"] - r["over"]) ** 2
        acc_goal += 1 if (r["p_goal"] > 0.5) == (r["goal"] == 1) else 0
        br_goal += (r["p_goal"] - r["goal"]) ** 2
        br_goal_base += (r["base_goal"] - r["goal"]) ** 2
        top = max(p)
        if top < 0.40:
            chiave = "sotto 40%"
        elif top < 0.50:
            chiave = "40-50%"
        elif top < 0.60:
            chiave = "50-60%"
        else:
            chiave = "60% o più"
        fasce[chiave].append((top, hit))
    righe_fasce = []
    for nome, lista in fasce.items():
        if lista:
            righe_fasce.append(
                {
                    "Fascia di probabilità": nome,
                    "Partite": len(lista),
                    "Prob. media": f"{sum(x[0] for x in lista) / len(lista) * 100:.1f}%",
                    "Azzeccate": f"{sum(x[1] for x in lista) / len(lista) * 100:.1f}%",
                }
            )
    return {
        "n": n,
        "acc": acc / n * 100,
        "acc_base": acc_base / n * 100,
        "brier": brier / n,
        "brier_base": brier_base / n,
        "acc_over": acc_over / n * 100,
        "br_over": br_over / n,
        "br_over_base": br_over_base / n,
        "acc_goal": acc_goal / n * 100,
        "br_goal": br_goal / n,
        "br_goal_base": br_goal_base / n,
        "fasce": righe_fasce,
    }


def mostra_backtest(matches, tab):
    with tab:
        st.subheader("🧪 Backtest del modello")
        st.caption(
            "Il modello rifà le previsioni sulle partite già giocate, usando "
            "solo i dati precedenti a ciascuna partita, e le confronta con "
            "il risultato vero. Usa solo i gol: i tiri in porta sono medie "
            "di stagione e falserebbero la prova."
        )
        giocate = _giocate_ordinate(matches)
        if len(giocate) < 40:
            st.info(
                "Servono almeno 40 partite giocate. Prova con la stagione 2025-26."
            )
            return

        c1, c2 = st.columns(2)
        with c1:
            rodaggio = st.selectbox(
                "Partite di rodaggio",
                [30, 50, 100],
                index=1,
                key=f"bt_rodaggio_{campionato_top}_{stagione_selezionata}",
            )
        with c2:
            d_scelto = st.selectbox(
                "Peso forma recente",
                [1.00, 0.98, 0.95, 0.90],
                index=2,
                format_func=lambda x: "1.00 (nessun peso)" if x == 1.0 else f"{x:.2f}",
                key=f"bt_peso_{campionato_top}_{stagione_selezionata}",
            )
        if len(giocate) < rodaggio + 20:
            st.info("Poche partite dopo il rodaggio: scegli meno rodaggio o un'altra stagione.")
            return

        confronto = []
        dettaglio = None
        with st.spinner("Calcolo in corso..."):
            for d in [1.00, 0.98, 0.95, 0.90]:
                ris = esegui_backtest(
                    matches, campionato_top, stagione_selezionata, d, rodaggio
                )
                s = riassumi_backtest(ris)
                if not s:
                    continue
                confronto.append(
                    {
                        "Peso forma": "1.00 (nessun peso)" if d == 1.0 else f"{d:.2f}",
                        "Partite testate": s["n"],
                        "Esiti azzeccati": f"{s['acc']:.1f}%",
                        "Errore Brier": round(s["brier"], 3),
                    }
                )
                if d == d_scelto:
                    dettaglio = s
        if not dettaglio:
            st.info("Dati insufficienti per questo torneo.")
            return

        confronto.append(
            {
                "Peso forma": "Riferimento (frequenze di lega)",
                "Partite testate": dettaglio["n"],
                "Esiti azzeccati": f"{dettaglio['acc_base']:.1f}%",
                "Errore Brier": round(dettaglio["brier_base"], 3),
            }
        )
        st.markdown("**Confronto tra impostazioni**")
        st.dataframe(pd.DataFrame(confronto), use_container_width=True, hide_index=True)

        s = dettaglio
        st.markdown(f"**Dettaglio con peso {d_scelto:.2f}** ({s['n']} partite testate)")
        m1, m2 = st.columns(2)
        m1.metric(
            "Esiti 1X2 azzeccati",
            f"{s['acc']:.1f}%",
            delta=f"{s['acc'] - s['acc_base']:+.1f} punti vs riferimento",
        )
        m2.metric(
            "Errore Brier 1X2",
            f"{s['brier']:.3f}",
            delta=f"{s['brier'] - s['brier_base']:+.3f} vs riferimento",
            delta_color="inverse",
        )
        m3, m4 = st.columns(2)
        m3.metric(
            "Over 2.5 azzeccato",
            f"{s['acc_over']:.1f}%",
            delta=f"Brier {s['br_over'] - s['br_over_base']:+.3f}",
            delta_color="inverse",
        )
        m4.metric(
            "Goal azzeccato",
            f"{s['acc_goal']:.1f}%",
            delta=f"Brier {s['br_goal'] - s['br_goal_base']:+.3f}",
            delta_color="inverse",
        )

        st.markdown("**Calibrazione: se dice 60%, succede 6 volte su 10?**")
        st.dataframe(pd.DataFrame(s["fasce"]), use_container_width=True, hide_index=True)
        st.caption(
            "Brier: più basso è meglio, tirare a caso (un terzo per esito) dà "
            "0.667. Il riferimento usa solo le frequenze storiche della lega. "
            "Se il modello non batte il riferimento, non aggiunge informazione. "
            "Con poche centinaia di partite, differenze di uno o due punti "
            "possono essere solo fortuna."
            )

def migliore_giocata(e, t1, t2, doppia_chance=False):
    opzioni = [
        (f"1 - {t1}", e["1"]),
        (f"2 - {t2}", e["2"]),
        ("Over 2.5", e["over25"]),
        ("Under 2.5", e["under25"]),
        ("Goal", e["goal"]),
        ("NoGoal", e["nogoal"]),
    ]
    if doppia_chance:
        opzioni.append(("1X", e["1"] + e["X"]))
        opzioni.append(("X2", e["X"] + e["2"]))
    return max(opzioni, key=lambda x: x[1])


def stelle_difficolta(p):
    if p >= 60:
        return "⭐ Medio"
    if p >= 50:
        return "⭐⭐ Difficile"
    return "⭐⭐⭐ Molto difficile"


def stelle_multipla(p):
    if p >= 40:
        return "⭐ Medio"
    if p >= 20:
        return "⭐⭐ Difficile"
    return "⭐⭐⭐ Molto difficile"


@st.cache_data(ttl=1800, show_spinner=False)
def raccogli_consigli(stagione, giorni, doppia_chance):
    oggi = now.strftime("%Y-%m-%d")
    limite = (now + timedelta(days=giorni)).strftime("%Y-%m-%d")
    consigli = []
    for camp in campionati_disponibili:
        dati = carica_dati_campionato(camp, stagione)
        matches = dati.get("matches", [])
        modello = calcola_forze(matches)
        if not modello:
            continue
        df = carica_stats_extra(camp, stagione)
        tiri = forze_tiri(df)
        nomi = set()
        if tiri is not None and df is not None:
            nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
        cache_nomi = {}

        def nome_fd(t):
            if t not in cache_nomi:
                cache_nomi[t] = trova_nome_fd(t, nomi) if nomi else None
            return cache_nomi[t]

        for m in matches:
            if not isinstance(m, dict):
                continue
            t1, t2 = m.get("team1"), m.get("team2")
            if not t1 or not t2:
                continue
            sc = m.get("score")
            if isinstance(sc, dict) and sc.get("ft"):
                continue
            data = str(m.get("date", ""))
            if data < oggi or data > limite:
                continue
            if t1 not in modello["forze"] or t2 not in modello["forze"]:
                continue
            l1, l2, _ = gol_attesi(modello, t1, t2, tiri, nome_fd(t1), nome_fd(t2))
            e = esiti_poisson(l1, l2)
            giocata, p = migliore_giocata(e, t1, t2, doppia_chance)
            consigli.append(
                {
                    "campionato": camp,
                    "data": data,
                    "partita": f"{t1} - {t2}",
                    "giocata": giocata,
                    "p": p,
                }
            )
    consigli.sort(key=lambda c: c["p"], reverse=True)
    return consigli


def mostra_ai_advice(tab):
    with tab:
        st.subheader("💡 AI Advice")
        st.caption(
            "Le partite con le previsioni più solide secondo il modello. "
            "Non confronta le quote dei bookmaker, quindi non può dire se "
            "una giocata ha valore: misura solo quanto il modello è sicuro. "
            "Nessuna giocata è garantita. Gioca responsabilmente, solo se "
            "maggiorenne e solo somme che puoi permetterti di perdere."
        )
        c1, c2 = st.columns(2)
        with c1:
            finestra = st.selectbox(
                "Partite in arrivo",
                ["Prossimi 3 giorni", "Prossimi 7 giorni", "Prossimi 14 giorni"],
                index=1,
                key="advice_finestra",
            )
        with c2:
            doppia = st.checkbox(
                "Includi doppia chance (1X, X2)", value=False, key="advice_doppia"
            )

        giorni = int(finestra.split()[1])
        with st.spinner("Analisi di tutti i campionati..."):
            consigli = raccogli_consigli(stagione_selezionata, giorni, doppia)
        if not consigli:
            st.info(
                "Nessuna partita trovata nel periodo. Prova una finestra più "
                "ampia o un'altra stagione."
            )
            return

        top = consigli[:10]
        st.markdown("**Top 10 giocate**")
        righe = [
            {
                "Difficoltà": stelle_difficolta(c["p"]),
                "Partita": c["partita"],
                "Giocata": c["giocata"],
                "Prob. %": round(c["p"], 1),
                "Quota equa": round(100 / c["p"], 2),
                "Data": c["data"],
                "Campionato": c["campionato"],
            }
            for c in top
        ]
        st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)

        st.markdown("**Multiple**")
        schemi = [("Doppia", 2), ("Tripla", 3), ("Quintupla", 5)]
        for nome, k in schemi:
            gambe = top[:k]
            if len(gambe) < k:
                continue
            prob = 1.0
            for g in gambe:
                prob *= g["p"] / 100
            testo = f"**{nome}** - {stelle_multipla(prob * 100)}  \n"
            testo += (
                f"Probabilità combinata **{prob * 100:.1f}%**, "
                f"quota equa **{1 / prob:.2f}**  \n"
            )
            for g in gambe:
                testo += f"• {g['partita']}: {g['giocata']} ({g['p']:.1f}%)  \n"
            st.markdown(testo)

        st.caption(
            "La probabilità di una multipla è il prodotto di quelle delle "
            "singole giocate, quindi scende in fretta. La quota equa non "
            "include il margine del bookmaker: le quote reali sono più basse. "
            "Le stelle indicano la difficoltà: più sono, meno è probabile."
        )
        coperti = sorted({c["campionato"] for c in consigli})
        st.caption("Campionati con dati: " + ", ".join(coperti) + ".")
import itertools
import json
import uuid

STATI_SCHEDINA = ["In attesa", "Vinta", "Persa"]


def quota_totale(quote):
    totale = 1.0
    for q in quote:
        totale *= q
    return totale


def calcola_multipla(quote, puntata, bonus_pct=0.0, quota_min=1.25,
                     eventi_min=5, base_netta=True):
    qt = quota_totale(quote)
    lorda = puntata * qt
    validi = sum(1 for q in quote if q >= quota_min)
    attivo = bonus_pct > 0 and validi >= eventi_min
    bonus = 0.0
    if attivo:
        base = (lorda - puntata) if base_netta else lorda
        bonus = base * bonus_pct / 100
    return {
        "quota_tot": qt,
        "lorda": lorda,
        "bonus": bonus,
        "totale": lorda + bonus,
        "validi": validi,
        "attivo": attivo,
    }


def calcola_sistema(quote, k, puntata_comb, vinte=None):
    n = len(quote)
    maschere = []
    prodotti = []
    for combo in itertools.combinations(range(n), k):
        m = 0
        p = 1.0
        for i in combo:
            m |= 1 << i
            p *= quote[i]
        maschere.append(m)
        prodotti.append(p)
    pieno = (1 << n) - 1

    def ritorno(vincenti):
        return puntata_comb * sum(
            p for m, p in zip(maschere, prodotti) if (m & vincenti) == m
        )

    puntata_tot = puntata_comb * len(maschere)
    if vinte is None:
        vinte = list(range(n))
    maschera_sim = 0
    for i in vinte:
        maschera_sim |= 1 << i

    tabella = []
    for errori in range(0, n - k + 1):
        valori = []
        for persi in itertools.combinations(range(n), errori):
            m_persi = 0
            for i in persi:
                m_persi |= 1 << i
            valori.append(ritorno(pieno & ~m_persi))
        tabella.append(
            {
                "Partite sbagliate": errori,
                "Ritorno minimo": round(min(valori), 2),
                "Ritorno massimo": round(max(valori), 2),
                "Netto minimo": round(min(valori) - puntata_tot, 2),
                "Netto massimo": round(max(valori) - puntata_tot, 2),
            }
        )
    return {
        "combinazioni": len(maschere),
        "puntata_tot": puntata_tot,
        "massimo": ritorno(pieno),
        "simulato": ritorno(maschera_sim),
        "tabella": tabella,
    }


def statistiche_archivio(arch):
    chiuse = [a for a in arch if a.get("stato") in ("Vinta", "Persa")]
    puntato = sum(float(a.get("puntata", 0)) for a in chiuse)
    incassato = sum(
        float(a.get("incasso", 0)) for a in chiuse if a.get("stato") == "Vinta"
    )
    vinte = sum(1 for a in chiuse if a.get("stato") == "Vinta")
    return {
        "chiuse": len(chiuse),
        "vinte": vinte,
        "in_attesa": sum(1 for a in arch if a.get("stato") == "In attesa"),
        "puntato": puntato,
        "incassato": incassato,
        "netto": incassato - puntato,
        "pct": (vinte / len(chiuse) * 100) if chiuse else 0.0,
    }


def importa_archivio(testo, esistente):
    try:
        dati = json.loads(testo)
    except Exception:
        return esistente, "Testo non valido: incolla il backup completo."
    if not isinstance(dati, list):
        return esistente, "Il backup non ha il formato giusto."
    ids = {a.get("id") for a in esistente}
    nuovi = [
        a for a in dati
        if isinstance(a, dict) and a.get("id") and a["id"] not in ids and "puntata" in a
    ]
    return esistente + nuovi, f"Importate {len(nuovi)} schedine."
def mostra_schedina(tab):
    with tab:
        st.subheader("🧾 Schedina")
        st.caption(
            "Inserisci partite e quote: calcola quota totale, bonus e vincita "
            "potenziale, per multipla o per sistema. Puoi salvare le giocate "
            "e tenere il conto di quanto hai puntato e incassato."
        )
        if "slip_df" not in st.session_state:
            st.session_state.slip_df = pd.DataFrame(
                {
                    "Partita": pd.Series([], dtype="object"),
                    "Giocata": pd.Series([], dtype="object"),
                    "Quota": pd.Series([], dtype="float"),
                    "Vinta": pd.Series([], dtype="bool"),
                    "Elimina": pd.Series([], dtype="bool"),
                }
            )
        if "slip_ver" not in st.session_state:
            st.session_state.slip_ver = 0
        if "slip_arch" not in st.session_state:
            st.session_state.slip_arch = []
        if "arch_ver" not in st.session_state:
            st.session_state.arch_ver = 0

        with st.form("slip_add", clear_on_submit=True):
            partita = st.text_input("Partita", placeholder="es. Inter - Parma")
            giocata = st.text_input("Giocata", placeholder="es. 1, Over 2.5, Goal")
            quota = st.number_input(
                "Quota", min_value=1.01, value=1.50, step=0.01, format="%.2f"
            )
            aggiungi = st.form_submit_button("➕ Aggiungi alla schedina")
        if aggiungi and partita.strip():
            nuova = pd.DataFrame(
                [
                    {
                        "Partita": partita.strip(),
                        "Giocata": giocata.strip(),
                        "Quota": float(quota),
                        "Vinta": True,
                        "Elimina": False,
                    }
                ]
            )
            base_df = st.session_state.slip_df
            if len(base_df) == 0:
                st.session_state.slip_df = nuova
            else:
                st.session_state.slip_df = pd.concat(
                    [base_df, nuova], ignore_index=True
                )
            st.session_state.slip_ver += 1
            st.rerun()

        df = st.session_state.slip_df
        if len(df) == 0:
            st.info("La schedina è vuota: aggiungi la prima selezione.")
        else:
            edited = st.data_editor(
                df,
                key=f"slip_ed_{st.session_state.slip_ver}",
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                column_config={
                    "Quota": st.column_config.NumberColumn(
                        "Quota", min_value=1.0, step=0.01, format="%.2f"
                    ),
                    "Vinta": st.column_config.CheckboxColumn("Vinta (simula)"),
                    "Elimina": st.column_config.CheckboxColumn("🗑"),
                },
            )
            st.session_state.slip_df = edited
            b1, b2 = st.columns(2)
            with b1:
                if st.button("🗑 Rimuovi spuntate", key="slip_rimuovi"):
                    st.session_state.slip_df = edited[~edited["Elimina"]].reset_index(
                        drop=True
                    )
                    st.session_state.slip_ver += 1
                    st.rerun()
            with b2:
                if st.button("Svuota schedina", key="slip_svuota"):
                    st.session_state.slip_df = edited.iloc[0:0]
                    st.session_state.slip_ver += 1
                    st.rerun()

            validi = edited[edited["Quota"].notna() & (edited["Quota"] >= 1.0)]
            quote = [float(q) for q in validi["Quota"]]
            n = len(quote)
            vinte_idx = [i for i, v in enumerate(validi["Vinta"]) if bool(v)]

            tipo = st.radio(
                "Tipo di giocata", ["Multipla", "Sistema"], horizontal=True,
                key="slip_tipo",
            )
            etichetta = "Puntata (€)" if tipo == "Multipla" else "Puntata per combinazione (€)"
            puntata = st.number_input(
                etichetta, min_value=0.5, value=10.0, step=0.5, key="slip_puntata"
            )

            potenziale = 0.0
            puntata_tot = puntata
            tipo_label = "Multipla"
            quota_tot_salva = None

            if tipo == "Multipla":
                with st.expander("Bonus multipla (dipende dal tuo operatore)"):
                    bonus_pct = st.number_input(
                        "Bonus multipla (%)", min_value=0.0, max_value=500.0,
                        value=0.0, step=0.5, key="slip_bonus",
                    )
                    quota_min = st.number_input(
                        "Quota minima valida per evento", min_value=1.0, value=1.25,
                        step=0.01, format="%.2f", key="slip_qmin",
                    )
                    eventi_min = st.number_input(
                        "Eventi minimi per il bonus", min_value=1, value=5, step=1,
                        key="slip_emin",
                    )
                    base = st.radio(
                        "Il bonus si applica alla",
                        ["Vincita netta (senza puntata)", "Vincita lorda"],
                        key="slip_base",
                    )
                r = calcola_multipla(
                    quote, puntata, bonus_pct, quota_min, int(eventi_min),
                    base.startswith("Vincita netta"),
                )
                if bonus_pct > 0 and not r["attivo"]:
                    st.warning(
                        f"Bonus non attivo: eventi validi {r['validi']} su "
                        f"{int(eventi_min)} richiesti (quota almeno {quota_min:.2f})."
                    )
                m1, m2 = st.columns(2)
                m1.metric("Quota totale", f"{r['quota_tot']:.2f}")
                m2.metric("Vincita senza bonus", f"{r['lorda']:.2f} €")
                m3, m4 = st.columns(2)
                m3.metric("Bonus", f"{r['bonus']:.2f} €")
                m4.metric("Totale potenziale", f"{r['totale']:.2f} €")
                st.caption(
                    f"Guadagno netto se vinci: {r['totale'] - puntata:.2f} €. "
                    "Controlla sempre il calcolo sul sito del tuo operatore."
                )
                potenziale = r["totale"]
                quota_tot_salva = r["quota_tot"]
            else:
                if n < 3:
                    st.info("Per un sistema servono almeno 3 selezioni.")
                elif n > 10:
                    st.info("Per i sistemi il massimo è 10 selezioni.")
                else:
                    k = st.selectbox(
                        "Sistema",
                        list(range(2, n)),
                        format_func=lambda x: f"{x} su {n}",
                        key=f"slip_k_{n}",
                    )
                    s = calcola_sistema(quote, k, puntata, vinte_idx)
                    m1, m2 = st.columns(2)
                    m1.metric("Combinazioni", s["combinazioni"])
                    m2.metric("Puntata totale", f"{s['puntata_tot']:.2f} €")
                    m3, m4 = st.columns(2)
                    m3.metric("Vincita massima", f"{s['massimo']:.2f} €")
                    m4.metric(
                        "Esito simulato", f"{s['simulato']:.2f} €",
                        delta=f"{s['simulato'] - s['puntata_tot']:+.2f} €",
                    )
                    st.markdown("**Cosa succede se sbagli qualche partita**")
                    st.dataframe(
                        pd.DataFrame(s["tabella"]),
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.caption(
                        "L'esito simulato usa le caselle «Vinta» della tabella. "
                        "Con più errori di quelli in tabella perdi tutta la puntata. "
                        "Nei sistemi il bonus multipla di solito non si applica."
                    )
                    potenziale = s["massimo"]
                    puntata_tot = s["puntata_tot"]
                    tipo_label = f"Sistema {k}/{n}"

            with st.expander("💾 Salva questa schedina"):
                nome = st.text_input("Nome o nota", key="slip_nome")
                stato = st.selectbox("Stato", STATI_SCHEDINA, key="slip_stato")
                incasso_in = st.number_input(
                    "Incasso effettivo (€), solo se Vinta", min_value=0.0, value=0.0,
                    step=0.5, key="slip_incasso",
                )
                if st.button("Salva nell'archivio", key="slip_salva"):
                    if n == 0 or potenziale <= 0:
                        st.warning("Niente da salvare.")
                    else:
                        if stato == "Vinta":
                            incasso = incasso_in if incasso_in > 0 else potenziale
                        else:
                            incasso = 0.0
                        eventi = [
                            {
                                "partita": str(rw["Partita"]),
                                "giocata": str(rw["Giocata"]),
                                "quota": float(rw["Quota"]),
                            }
                            for _, rw in validi.iterrows()
                        ]
                        st.session_state.slip_arch.append(
                            {
                                "id": uuid.uuid4().hex[:8],
                                "data": now.strftime("%Y-%m-%d %H:%M"),
                                "nome": nome.strip(),
                                "tipo": tipo_label,
                                "puntata": round(float(puntata_tot), 2),
                                "quota_tot": quota_tot_salva,
                                "potenziale": round(float(potenziale), 2),
                                "stato": stato,
                                "incasso": round(float(incasso), 2),
                                "eventi": eventi,
                            }
                        )
                        st.session_state.arch_ver += 1
                        st.success("Schedina salvata nell'archivio qui sotto.")

        st.divider()
        st.markdown("### 📚 Archivio giocate")
        arch = st.session_state.slip_arch
        if not arch:
            st.info("Nessuna schedina salvata.")
        else:
            riquadro = st.container()
            tab_arch = pd.DataFrame(
                [
                    {
                        "ID": a["id"],
                        "Data": a["data"],
                        "Nome": a["nome"],
                        "Tipo": a["tipo"],
                        "Puntata": a["puntata"],
                        "Potenziale": a["potenziale"],
                        "Stato": a["stato"],
                        "Incasso": a["incasso"],
                        "Elimina": False,
                    }
                    for a in arch
                ]
            )
            mod = st.data_editor(
                tab_arch,
                key=f"arch_ed_{st.session_state.arch_ver}",
                use_container_width=True,
                hide_index=True,
                disabled=["Data", "Nome", "Tipo", "Puntata", "Potenziale"],
                column_config={
                    "ID": None,
                    "Stato": st.column_config.SelectboxColumn(
                        "Stato", options=STATI_SCHEDINA, required=True
                    ),
                    "Incasso": st.column_config.NumberColumn(
                        "Incasso", min_value=0.0, step=0.5, format="%.2f"
                    ),
                    "Elimina": st.column_config.CheckboxColumn("🗑"),
                },
            )
            per_id = {a["id"]: a for a in arch}
            for _, rw in mod.iterrows():
                a = per_id.get(rw["ID"])
                if not a:
                    continue
                a["stato"] = rw["Stato"]
                if rw["Stato"] == "Vinta":
                    inc = float(rw["Incasso"])
                    a["incasso"] = inc if inc > 0 else a["potenziale"]
                else:
                    a["incasso"] = 0.0
            stt = statistiche_archivio(arch)
            with riquadro:
                a1, a2 = st.columns(2)
                a1.metric("Puntato (chiuse)", f"{stt['puntato']:.2f} €")
                a2.metric("Incassato", f"{stt['incassato']:.2f} €")
                a3, a4 = st.columns(2)
                a3.metric("Netto", f"{stt['netto']:+.2f} €")
                a4.metric(
                    "Vinte", f"{stt['vinte']}/{stt['chiuse']}",
                    delta=f"{stt['pct']:.0f}%", delta_color="off",
                )
                if stt["in_attesa"]:
                    st.caption(f"{stt['in_attesa']} schedine ancora in attesa.")
            if st.button("🗑 Rimuovi spuntate", key="arch_rimuovi"):
                da_togliere = set(mod.loc[mod["Elimina"], "ID"])
                st.session_state.slip_arch = [
                    a for a in arch if a["id"] not in da_togliere
                ]
                st.session_state.arch_ver += 1
                st.rerun()

            etichette = {
                f"{a['data']} | {a['nome'] or '(senza nome)'} | {a['tipo']}": a
                for a in arch
            }
            scelta = st.selectbox(
                "Dettaglio schedina", list(etichette.keys()), key="arch_dettaglio"
            )
            ev = etichette[scelta].get("eventi", [])
            if ev:
                st.dataframe(
                    pd.DataFrame(ev), use_container_width=True, hide_index=True
                )

        with st.expander("📤 Backup e importazione"):
            st.caption(
                "L'archivio vive solo finché l'app resta aperta: se la pagina "
                "si ricarica o l'app si riavvia, si cancella. Copia il testo "
                "qui sotto (pulsante in alto a destra del riquadro) e salvalo "
                "nelle note del telefono."
            )
            testo = json.dumps(st.session_state.slip_arch, ensure_ascii=False)
            st.code(testo, language="json")
            st.download_button(
                "Scarica file", testo, file_name="schedine.json",
                mime="application/json", key="arch_download",
            )
            incolla = st.text_area(
                "Incolla qui un backup per importarlo", key="arch_incolla"
            )
            if st.button("Importa", key="arch_importa"):
                nuovo, msg = importa_archivio(incolla, st.session_state.slip_arch)
                st.session_state.slip_arch = nuovo
                st.session_state.arch_ver += 1
                st.info(msg)

def sezione_confronto(matches):
    oggi = now.strftime("%Y-%m-%d")
    prossime = [
        m
        for m in matches
        if isinstance(m, dict)
        and m.get("team1")
        and m.get("team2")
        and str(m.get("date", "")) >= oggi
    ]

    if not prossime:
        st.info("Nessuna partita futura disponibile per questo torneo/stagione.")
        return

    match_dict = {
        f"{m.get('date', 'Data n.d.')} | {m['team1']} vs {m['team2']}": m
        for m in prossime
    }

    st.markdown("🎯 *Seleziona una partita per il Confronto Diretto e Pronostico IA:*")
    scelta = st.selectbox(
        "Seleziona la Partita della Giornata",
        list(match_dict.keys()),
        key=f"match_scelto_{campionato_top}_{stagione_selezionata}",
    )

    m_sel = match_dict[scelta]
    t1, t2 = m_sel["team1"], m_sel["team2"]

    stats_t1 = calcola_statistiche_squadra(matches, t1)
    stats_t2 = calcola_statistiche_squadra(matches, t2)
    prob_1, prob_x, prob_2 = calcola_pronostico_ia(stats_t1, stats_t2)
    prob_1, prob_x, prob_2, dettagli_v2 = probabilita_v2(matches, t1, t2, stats_t1, stats_t2)
    
    st.markdown("---")
    st.markdown(f"### ⚔️ Confronto Diretto: {t1} vs {t2}")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        mostra_metriche_squadra(f"#### 🏠 {badge_squadra(t1)} {t1}", stats_t1)
    with col_s2:
        mostra_metriche_squadra(f"#### ✈️ {badge_squadra(t2)} {t2}", stats_t2)
    mostra_scontri_diretti(campionato_top, t1, t2)
    mostra_grafico_forma({t1: stats_t1, t2: stats_t2})
    mostra_stats_tempi(f"#### ⏱️ Gol per tempo: {t1}", calcola_stats_tempi(matches, t1))
    mostra_stats_tempi(f"#### ⏱️ Gol per tempo: {t2}", calcola_stats_tempi(matches, t2))
    mostra_stats_extra(f"#### 📊 Angoli e tiri: {t1}", t1)
    mostra_stats_extra(f"#### 📊 Angoli e tiri: {t2}", t2)
    mostra_pronostico_v2(matches, t1, t2)
    st.markdown("---")
    analisi = genera_analisi_ia_match(t1, t2, prob_1, prob_x, prob_2)
    analisi = genera_analisi_v2(t1, t2, prob_1, prob_x, prob_2, dettagli_v2)
    st.markdown(
        f"<div class='ai-box'>{analisi}<br><br><b>Previsioni Esito 1X2:</b><br>"
        f"• {t1} (1): <b>{prob_1}%</b><br>"
        f"• Pareggio (X): <b>{prob_x}%</b><br>"
        f"• {t2} (2): <b>{prob_2}%</b></div>",
        unsafe_allow_html=True,
        )
if st.session_state.pagina == "home":
    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; padding: 35px; border-radius: 16px; margin-top: 20px; text-align: center;'>
            <h1 style='color: #58a6ff; font-size: 38px; margin-bottom: 10px;'>⚽ b-betting Hub</h1>
            <p style='color: #8b949e; font-size: 16px; margin-bottom: 30px;'>Piattaforma avanzata di Live Data Architecture, Statistiche Sportive e Previsioni Algoritmiche.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_h1, col_h2, col_h3 = st.columns([1, 2, 1])
    with col_h2:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        if st.button(
            "🚀 ACCEDI ALLA DASHBOARD", use_container_width=True, type="primary"
        ):
            st.session_state.pagina = "dashboard"
            st.rerun()

    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

    feature_box = (
        "<div style='background: #161b22; padding: 20px; border-radius: 12px;"
        " border: 1px solid #30363d; text-align: center;'><h3>{icona}</h3>"
        "<h4>{titolo}</h4><p style='color: #8b949e; font-size: 13px;'>{testo}</p></div>"
    )
    col_feat1, col_feat2, col_feat3 = st.columns(3)
    with col_feat1:
        st.markdown(
            feature_box.format(
                icona="📅",
                titolo="Palinsesto Live",
                testo="Consulta calendari e partite aggiornate dai principali tornei.",
            ),
            unsafe_allow_html=True,
        )
    with col_feat2:
        st.markdown(
            feature_box.format(
                icona="📊",
                titolo="Classifiche Aggiornate",
                testo="Analizza punti, gol fatti, subiti e differenza reti.",
            ),
            unsafe_allow_html=True,
        )
    with col_feat3:
        st.markdown(
            feature_box.format(
                icona="🤖",
                titolo="Analisi IA & Pronostici",
                testo="Algoritmi predittivi per stimare le probabilità di match.",
            ),
            unsafe_allow_html=True,
        )

else:
    col_title, col_home_btn = st.columns([0.80, 0.20])
    with col_title:
        st.title("⚽ b-betting")
        st.markdown(
    "<p style='color:#8b949e; font-size:14px; margin-top:-10px;'>"
    "Football Statistics • Analysis • Probabilities"
    "</p>",
    unsafe_allow_html=True,
        )
    with col_home_btn:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🏠 Home", use_container_width=True, help="Torna alla Home"):
            st.session_state.pagina = "home"
            st.rerun()

    st.divider()

    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; padding: 25px; border-radius: 16px; margin-bottom: 20px;'>
            <h2 style='color: #58a6ff; margin-bottom: 5px;'>⚽ b-betting Hub</h2>
            <p style='color: #8b949e; font-size: 14px; margin-top: 0;'>Piattaforma avanzata di Live Data Architecture, Statistiche Sportive e Previsioni Algoritmiche.</p>
            <div style='display: flex; gap: 10px; flex-wrap: wrap; margin-top: 15px;'>
                <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>⚡ Engine: <b>Attivo</b></span>
                <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>📊 Modello IA: <b>v4.2 Pro</b></span>
                <span style='background: #21262d; border: 1px solid #30363d; padding: 4px 12px; border-radius: 20px; font-size: 12px; color: #c9d1d9;'>🕒 Sync: <b>Real-time</b></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    data = carica_dati_campionato(campionato_top, stagione_selezionata)
    matches = data.get("matches", [])

    tab1, tab2, tab3, tab4,tab5,tab6,tab7 = st.tabs(
        ["📅 Palinsesto", "📊 Classifica", "📈 Analisi Match & Statistiche", "🎯 Riepilogo", "🧪 Backtest", "💡 AI Advice", "🧾 Schedina"]
    )
    mostra_riepilogo(matches, tab4)
    mostra_backtest(matches, tab5)
    mostra_ai_advice(tab6)
    mostra_schedina(tab7)
    with tab1:
        st.subheader("Palinsesto Match")
        partite = [m for m in matches if isinstance(m, dict)]
        if partite:
            giornate = []
            for m in partite:
                g = m.get("round")
                if g and g not in giornate:
                    giornate.append(g)

            filtro = "Tutte le giornate"
            if giornate:
                filtro = st.selectbox(
                    "Filtra per giornata",
                    ["Tutte le giornate"] + giornate,
                    key=f"filtro_giornata_{campionato_top}_{stagione_selezionata}",
                )

            lista = []
            for m in partite:
                if filtro != "Tutte le giornate" and m.get("round") != filtro:
                    continue
                sc = m.get("score")
                ft = sc.get("ft") if isinstance(sc, dict) else None
                lista.append(
                    {
                        "Giornata": m.get("round", ""),
                        "Data": m.get("date", ""),
                        "Casa": m.get("team1", ""),
                        "Ospite": m.get("team2", ""),
                        "Risultato": f"{ft[0]}-{ft[1]}" if ft else "-",
                    }
                )
            st.dataframe(
                pd.DataFrame(lista), use_container_width=True, hide_index=True
            )
        else:
            st.warning("Dati non disponibili per questo torneo.")

    with tab2:
        st.subheader("Classifica Live")
        classifica = {}
        for m in matches:
            if (
                isinstance(m, dict)
                and isinstance(m.get("score"), dict)
                and m["score"].get("ft")
            ):
                t1, t2 = m.get("team1"), m.get("team2")
                if not t1 or not t2:
                    continue
                g1, g2 = m["score"]["ft"][0], m["score"]["ft"][1]
                for sq in (t1, t2):
                    if sq not in classifica:
                        classifica[sq] = {
                            "Squadra": sq,
                            "PG": 0,
                            "Pt": 0,
                            "GF": 0,
                            "GS": 0,
                        }
                classifica[t1]["PG"] += 1
                classifica[t2]["PG"] += 1
                classifica[t1]["GF"] += g1
                classifica[t1]["GS"] += g2
                classifica[t2]["GF"] += g2
                classifica[t2]["GS"] += g1
                if g1 > g2:
                    classifica[t1]["Pt"] += 3
                elif g1 < g2:
                    classifica[t2]["Pt"] += 3
                else:
                    classifica[t1]["Pt"] += 1
                    classifica[t2]["Pt"] += 1

        if classifica:
            df_c = pd.DataFrame(list(classifica.values()))
            df_c["DR"] = df_c["GF"] - df_c["GS"]
            df_c = df_c.sort_values(
                by=["Pt", "DR"], ascending=False
            ).reset_index(drop=True)
            df_c.index += 1
            st.dataframe(df_c, use_container_width=True)
        else:
            st.warning("Classifica non disponibile.")

    with tab3:
        st.subheader("📊 Analisi Match & Statistiche")

        tutte_squadre = sorted(
            {m.get("team1") for m in matches if isinstance(m, dict) and m.get("team1")}
            | {m.get("team2") for m in matches if isinstance(m, dict) and m.get("team2")}
        )

        if not tutte_squadre:
            st.warning("Dati non disponibili per questo torneo.")
        else:
            st.markdown("🔍 **Cerca Statistiche per Singola Squadra:**")
            squadra_singola = st.selectbox(
                "Seleziona o digita una squadra per visualizzare le sue statistiche",
                ["-- Seleziona una squadra --"] + tutte_squadre,
                key="ricerca_singola_squadra",
            )

            if squadra_singola != "-- Seleziona una squadra --":
                st.markdown(f"### 📋 Report: {badge_squadra(squadra_singola)} {squadra_singola}", unsafe_allow_html=True)
                stats_singola = calcola_statistiche_squadra(matches, squadra_singola)
                if stats_singola:
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("Punti a Partita (PPG)", stats_singola["ppg"])
                        st.metric("Partite Giocate", stats_singola["tot"])
                    with c2:
                        st.metric("Media Gol Fatti", stats_singola["gf_avg"])
                        st.metric("Over 2.5 %", f"{stats_singola['over_2_5_pct']}%")
                    with c3:
                        st.metric("Media Gol Subiti", stats_singola["gs_avg"])
                        st.metric(
                            "Clean Sheet %", f"{stats_singola['clean_sheets_pct']}%"
                        )
                    with c4:
                        st.metric("BTTS %", f"{stats_singola['btts_pct']}%")

                    st.markdown("**Stato di Forma (Ultime 5):**")
                    classi = {"V": "badge-v", "N": "badge-n", "P": "badge-p"}
                    forma_html = "".join(
                        f"<span class='{classi[r]}'>{r}</span>"
                        for r in stats_singola["forma"][-5:]
                    )
                    st.markdown(forma_html or "N.D.", unsafe_allow_html=True)
                    mostra_stats_tempi("#### ⏱️ Gol per tempo", calcola_stats_tempi(matches, squadra_singola))
                    mostra_grafico_forma({squadra_singola: stats_singola})
                    mostra_stats_extra("#### 📊 Angoli, tiri e disciplina", squadra_singola)
                else:
                    st.info(
                        "Nessun dato di match disputati disponibile per questa"
                        " squadra nella stagione selezionata."
                    )

            st.markdown("---")
            sezione_confronto(matches)

