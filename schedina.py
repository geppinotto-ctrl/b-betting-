import itertools
import json
import pandas as pd
import streamlit as st
import uuid
from config import adesso
from quote import aggiungi_alla_schedina, etichetta_slip, ottieni_catalogo_partita, selettore_giocata


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


def mostra_schedina(tab, matches=None):
    with tab:
        st.subheader("📝 Schedina")
        st.caption("Seleziona partite e quote dai menu a tendina: calcola quota totale, bonus e vincita potenziale.")

        # Inizializzazione sicura di tutte le variabili di sessione necessarie
        if 'slip_df' not in st.session_state:
            st.session_state.slip_df = pd.DataFrame({
                "Partita": pd.Series([], dtype="object"),
                "Giocata": pd.Series([], dtype="object"),
                "Quota": pd.Series([], dtype="float"),
                "Vinta": pd.Series([], dtype="bool"),
                "Elimina": pd.Series([], dtype="bool"),
            })
        if 'slip_ver' not in st.session_state:
            st.session_state.slip_ver = 0
        if 'slip_arch' not in st.session_state:
            st.session_state.slip_arch = []
        if 'arch_ver' not in st.session_state:
            st.session_state.arch_ver = 0

        # Elenco COMPLETO delle partite caricate (stessa sorgente del Palinsesto)
        oggi_s = adesso().strftime("%Y-%m-%d")
        partite_valide = [
            m for m in (matches or [])
            if isinstance(m, dict) and m.get("team1") and m.get("team2")
        ]
        partite_valide.sort(key=lambda m: (str(m.get("date") or ""), str(m.get("time") or "")))
        # solo partite ancora da giocare: niente date passate né gare con risultato
        partite_valide = [
            m for m in partite_valide
            if str(m.get("date") or "")[:10] >= oggi_s
            and not (isinstance(m.get("score"), dict) and m["score"].get("ft"))
        ]
        mappa_partite = {}
        for m in partite_valide:
            etichetta = f'{m["team1"]} - {m["team2"]}'
            if m.get("date"):
                etichetta += f' ({str(m["date"])[:10]})'
            if etichetta not in mappa_partite:
                mappa_partite[etichetta] = m
        partite_disponibili = list(mappa_partite.keys())
        if not partite_disponibili:
            st.warning("⚠️ Nessuna partita da giocare per questo torneo/stagione: prova un altro campionato o un'altra stagione.")
            partite_disponibili = ["—"]

        # di default la prossima partita da giocare
        indice_prossima = 0
        for i, et in enumerate(partite_disponibili):
            mm = mappa_partite.get(et)
            if mm and str(mm.get("date") or "")[:10] >= oggi_s:
                indice_prossima = i
                break

        st.markdown("### 🔍 Schedina Rapida")
        if st.session_state.get("slip_msg"):
            st.success(st.session_state.slip_msg)
            st.session_state.slip_msg = None

        partita_selezionata = st.selectbox(
            "Seleziona Partita", options=partite_disponibili,
            index=indice_prossima, key="sel_partita_dinamica",
        )
        solo_it = st.checkbox("Solo bookmaker italiani (ADM)", value=True, key="slip_solo_it")

        m_sel = mappa_partite.get(partita_selezionata)
        cat, avviso = None, ""
        if m_sel:
            cat, _ev, avviso, _rec = ottieni_catalogo_partita(m_sel["team1"], m_sel["team2"], solo_it)

        if cat:
            if avviso:
                st.info(avviso)
            mercato, giocata, quota, book = selettore_giocata(cat, "slip")
            if st.button("➕ Aggiungi alla schedina", key="btn_aggiungi_schedina"):
                aggiungi_alla_schedina(
                    partita_selezionata, etichetta_slip(mercato, giocata), quota, "slip_msg"
                )
        else:
            st.info(
                (avviso + " " if avviso else "")
                + "Quota automatica non disponibile: scegli la giocata e inserisci la quota a mano."
            )
            opzioni_giocata = [
                "1X2: 1", "1X2: X", "1X2: 2", "1X", "X2", "12",
                "Over 1.5", "Under 1.5", "Over 2.5", "Under 2.5",
                "Over 3.5", "Under 3.5", "Over 4.5", "Under 4.5",
                "Goal", "No Goal", "Gol Pari", "Gol Dispari",
            ]
            giocata_selezionata = st.selectbox(
                "Seleziona Giocata", options=opzioni_giocata, key="sel_giocata_dinamica"
            )
            quota_man = st.number_input(
                "Quota", min_value=1.01, max_value=1000.0, value=1.50, step=0.01,
                format="%.2f", key="input_quota_dinamica",
            )
            if st.button("➕ Aggiungi alla schedina", key="btn_aggiungi_schedina"):
                aggiungi_alla_schedina(
                    partita_selezionata, giocata_selezionata, quota_man, "slip_msg"
                )

        # Visualizzazione e gestione della schedina attiva (un solo editor).
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
                                "data": adesso().strftime("%Y-%m-%d %H:%M"),
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
