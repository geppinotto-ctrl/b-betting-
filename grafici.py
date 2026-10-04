import html as _html

import pandas as pd
import streamlit as st

from modello import distribuzione_gol_totali, matrice_risultati
from stile import badge_squadra

COL_1, COL_X, COL_2 = "#2f81f7", "#8b949e", "#f78166"

CSS_GRAFICI = (
    "<style>"
    ".gx-card{background:rgba(22,27,34,0.62);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);"
    "border:1px solid rgba(255,255,255,0.09);border-radius:14px;padding:12px;margin:8px 0 12px 0;}"
    ".gx-top{display:flex;justify-content:space-between;gap:8px;font-size:11px;color:#8b949e;margin-bottom:8px;}"
    ".gx-teams{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:6px;}"
    ".gx-team{flex:1;min-width:0;color:#fff;font-weight:700;font-size:14px;line-height:1.25;}"
    ".gx-team.gx-r{text-align:right;}"
    ".gx-name{display:block;margin-top:4px;overflow-wrap:anywhere;}"
    ".gx-lab{font-size:10px;letter-spacing:1px;color:#8b949e;margin:8px 0 3px 0;text-transform:uppercase;}"
    ".gx-bar{display:flex;height:24px;border-radius:7px;overflow:hidden;background:rgba(255,255,255,0.06);}"
    ".gx-bar.gx-sm{height:16px;}"
    ".gx-seg{display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;}"
    ".gx-bar.gx-sm .gx-seg{font-size:10px;}"
    ".gx-foot{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;color:#c9d1d9;margin-top:10px;}"
    ".gx-foot b{color:#fff;}"
    ".gx-form{margin-top:4px;}"
    ".gx-f{display:inline-block;width:18px;height:18px;line-height:18px;text-align:center;border-radius:4px;color:#fff;font-size:10px;font-weight:700;margin-right:2px;}"
    ".gx-r .gx-f{margin-right:0;margin-left:2px;}"
    ".gx-r > span:first-child{margin-right:0 !important;}"
    ".gx-fv{background:#238636;}.gx-fn{background:#d29922;}.gx-fp{background:#da3633;}"
    ".gx-hm{border-collapse:separate;border-spacing:2px;margin:6px auto;}"
    ".gx-hm th{font-size:11px;color:#8b949e;font-weight:600;padding:2px 4px;}"
    ".gx-hm td{width:44px;height:30px;text-align:center;font-size:11px;color:#fff;border-radius:5px;}"
    ".gx-cap{font-size:11px;color:#8b949e;text-align:center;margin-top:2px;}"
    "</style>"
)


def forma_html(forma, n=5):
    if not forma:
        return ""
    cls = {"V": "gx-fv", "N": "gx-fn", "P": "gx-fp"}
    chips = "".join(
        f"<span class='gx-f {cls.get(r, 'gx-fn')}'>{_html.escape(str(r))}</span>"
        for r in forma[-n:]
    )
    return f"<div class='gx-form'>{chips}</div>"


def barra_1x2_html(p1, px, p2, etichetta="", piccola=False):
    tot = (p1 + px + p2) or 1.0
    seg = ""
    for val, col, lab in ((p1, COL_1, "1"), (px, COL_X, "X"), (p2, COL_2, "2")):
        w = val / tot * 100
        if w >= 16:
            testo = f"{lab} {val:.0f}%"
        elif w >= 8:
            testo = f"{val:.0f}%"
        else:
            testo = ""
        seg += f"<div class='gx-seg' style='width:{w:.1f}%;background:{col};'>{testo}</div>"
    et = f"<div class='gx-lab'>{_html.escape(etichetta)}</div>" if etichetta else ""
    return et + f"<div class='gx-bar{' gx-sm' if piccola else ''}'>{seg}</div>"


def scheda_html(t1, t2, p_mod, p_mkt=None, sopra_sx="", sopra_dx="",
                forma1=None, forma2=None, piede=""):
    top = ""
    if sopra_sx or sopra_dx:
        top = (f"<div class='gx-top'><span>{_html.escape(str(sopra_sx))}</span>"
               f"<span>{_html.escape(str(sopra_dx))}</span></div>")
    squadre = (
        "<div class='gx-teams'>"
        f"<div class='gx-team'>{badge_squadra(t1)}<span class='gx-name'>{_html.escape(t1)}</span>{forma_html(forma1)}</div>"
        f"<div class='gx-team gx-r'>{badge_squadra(t2)}<span class='gx-name'>{_html.escape(t2)}</span>{forma_html(forma2)}</div>"
        "</div>"
    )
    barre = barra_1x2_html(*p_mod, etichetta="Modello")
    if p_mkt:
        barre += barra_1x2_html(*p_mkt, etichetta="Mercato (senza margine)", piccola=True)
    foot = f"<div class='gx-foot'>{piede}</div>" if piede else ""
    return f"<div class='gx-card'>{top}{squadre}{barre}{foot}</div>"


def heatmap_html(m, nome1, nome2):
    n = len(m)
    pmax = max(max(r) for r in m) or 1.0
    testa = "<tr><th></th>" + "".join(f"<th>{j}</th>" for j in range(n)) + "</tr>"
    righe = ""
    for i, r in enumerate(m):
        celle = ""
        for j, v in enumerate(r):
            alfa = 0.10 + 0.85 * v / pmax
            stile = f"background:rgba(47,129,247,{alfa:.2f});"
            if v == pmax:
                stile += "outline:2px solid #f2cc60;"
            celle += f"<td style='{stile}'>{v:.1f}</td>"
        righe += f"<tr><th>{i}</th>{celle}</tr>"
    return (
        "<div class='gx-cap'>Righe: gol di "
        f"<b>{_html.escape(nome1)}</b> · Colonne: gol di <b>{_html.escape(nome2)}</b></div>"
        f"<table class='gx-hm'>{testa}{righe}</table>"
    )


def mostra_grafici_partita(t1, t2, stats1, stats2, p1, px, p2, dettagli, quando=""):
    st.markdown("### 📈 Scheda partita")
    piede = ""
    if dettagli:
        e = dettagli.get("e", {})
        piede = (
            f"<span>Gol attesi <b>{dettagli['l1']:.2f}</b> – <b>{dettagli['l2']:.2f}</b></span>"
            f"<span>Over 2.5 <b>{e.get('over25', 0):.0f}%</b></span>"
            f"<span>Goal <b>{e.get('goal', 0):.0f}%</b></span>"
        )
    st.markdown(
        CSS_GRAFICI + scheda_html(
            t1, t2, (p1, px, p2), sopra_sx=quando,
            forma1=(stats1 or {}).get("forma"), forma2=(stats2 or {}).get("forma"),
            piede=piede,
        ),
        unsafe_allow_html=True,
    )
    if not dettagli:
        return

    st.markdown("#### 🎯 Risultati esatti più probabili")
    m = matrice_risultati(dettagli["l1"], dettagli["l2"], 5)
    st.markdown(CSS_GRAFICI + heatmap_html(m, t1, t2), unsafe_allow_html=True)
    st.caption(
        "Ogni cella è la probabilità (%) di quel risultato esatto: più è chiara "
        "la tinta, meno è probabile. Il riquadro giallo è il più probabile."
    )

    st.markdown("#### ⚽ Quanti gol in totale")
    dist = distribuzione_gol_totali(dettagli["l1"], dettagli["l2"], 7)
    etichette = ["0", "1", "2", "3", "4", "5", "6", "7+"]
    valori = [round(dist.get(i, 0.0), 1) for i in range(8)]
    st.bar_chart(
        pd.DataFrame(
            {"Probabilità %": valori},
            index=etichette,
        )
    )
    
    

    


def schede_riepilogo(righe, mostra_tutte=False, limite=10):
    scelte = righe if mostra_tutte else righe[:limite]
    carte = ""
    for r in scelte:
        mk = r.get("_mk")
        p_mkt = (mk["1"], mk["X"], mk["2"]) if mk else None
        piede = (
            f"<span>Esito <b>{r['Esito']}</b> {r['Prob. esito']:.0f}%</span>"
            f"<span>Quota equa <b>{r['Quota equa']:.2f}</b></span>"
            f"<span>Over 2.5 <b>{r['Over 2.5']:.0f}%</b></span>"
            f"<span>Goal <b>{r['Goal']:.0f}%</b></span>"
        )
        if r.get("Scarto") is not None:
            piede += f"<span>Scarto dal mercato <b>{r['Scarto']:+.1f}</b></span>"
        carte += scheda_html(
            r["_t1"], r["_t2"], (r["1"], r["X"], r["2"]), p_mkt,
            sopra_sx=r["Data"], piede=piede,
        )
    st.markdown(CSS_GRAFICI + carte, unsafe_allow_html=True)
    if not mostra_tutte and len(righe) > limite:
        st.caption(f"Mostrate {limite} partite su {len(righe)}: spunta «Mostra tutte» per vederle tutte.")
