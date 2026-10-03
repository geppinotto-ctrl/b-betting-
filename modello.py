from datetime import timedelta
import math
import pandas as pd
import streamlit as st
from config import adesso, campionati_disponibili, stagione_corrente, torneo_corrente
from dati import carica_dati_campionato, carica_stats_extra, trova_nome_fd


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


def sintesi_dna_pronostico(t1, t2, dettagli):
    if not dettagli:
        return ""

    l1 = dettagli.get("l1", 0)
    l2 = dettagli.get("l2", 0)
    e = dettagli.get("e", {})

    p1 = e.get("1", 0)
    px = e.get("X", 0)
    p2 = e.get("2", 0)

    att1 = dettagli.get("att1", 1)
    dif1 = dettagli.get("dif1", 1)
    att2 = dettagli.get("att2", 1)
    dif2 = dettagli.get("dif2", 1)

    if p1 > p2:
        esito = f"{t1} emerge come esito principale"
    elif p2 > p1:
        esito = f"{t2} emerge come esito principale"
    else:
        esito = "il modello vede un equilibrio tra le due squadre"

    if l1 > l2:
        gol = f"{t1} ha una proiezione offensiva superiore ({l1:.2f} vs {l2:.2f} gol attesi)"
    elif l2 > l1:
        gol = f"{t2} ha una proiezione offensiva superiore ({l2:.2f} vs {l1:.2f} gol attesi)"
    else:
        gol = "le due squadre hanno la stessa proiezione di gol"

    if att1 > att2:
        attacco = f"{t1} presenta l'indice offensivo più alto"
    elif att2 > att1:
        attacco = f"{t2} presenta l'indice offensivo più alto"
    else:
        attacco = "gli indici offensivi sono equivalenti"

    return f"{esito}. {gol}; {attacco}. Probabilità 1X2: {p1:.1f}% / {px:.1f}% / {p2:.1f}%."


def probabilita_v2(matches, t1, t2, stats1, stats2):
    modello = calcola_forze(matches)
    if modello and t1 in modello["forze"] and t2 in modello["forze"]:
        df = carica_stats_extra(torneo_corrente(), stagione_corrente())
        tiri = forze_tiri(df)
        nome1 = nome2 = None
        if tiri is not None and df is not None:
            nomi = set(df["HomeTeam"].dropna()) | set(df["AwayTeam"].dropna())
            nome1 = trova_nome_fd(t1, nomi)
            nome2 = trova_nome_fd(t2, nomi)
        l1, l2, usato_tiri = gol_attesi(modello, t1, t2, tiri, nome1, nome2)
        e = esiti_poisson(l1, l2)
        dettagli = {
    "l1": l1,
    "l2": l2,
    "e": e,
    "tiri": usato_tiri,
    "mc": modello["mc"],
    "mf": modello["mf"],
    "att1": modello["forze"][t1]["att"],
    "dif1": modello["forze"][t1]["dif"],
    "att2": modello["forze"][t2]["att"],
    "dif2": modello["forze"][t2]["dif"],
        }
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
    oggi = adesso().strftime("%Y-%m-%d")
    limite = (adesso() + timedelta(days=giorni)).strftime("%Y-%m-%d")
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
