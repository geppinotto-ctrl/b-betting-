"""Pagina «Test previsioni»: registra tutte le partite di un perimetro e le valuta dopo.

Regole di interfaccia:
  * l'anteprima (quanto verrebbe registrato) si vede SEMPRE prima di salvare e non
    scrive nulla: è il «dry-run»;
  * si scrive solo premendo «Registra batch»: aprire la pagina o ricaricarla non
    registra niente;
  * l'«archivio di prova» è un file separato: serve a collaudare salvataggio,
    riavvio e backup senza sporcare quello vero (le previsioni vere non si cancellano).
"""

import time
from datetime import timedelta

import pandas as pd
import streamlit as st

import backup_remoto
import previsioni_batch as B
import previsioni_db as DB
from config import STAGIONI, adesso, campionati_disponibili, stagione_corrente, torneo_corrente
from dati import carica_dati_campionato, carica_stats_extra
from resilienza import ERRORE, OBSOLETO, OK, VUOTO, sezione_sicura


def pct(x):
    return "" if x is None else f"{x * 100:.1f}%"


def tabella_partite(righe):
    """DataFrame leggibile (percentuali) per le partite registrate."""
    out = []
    for r in righe:
        out.append({
            "Data": r["data"], "Partita": f"{r['casa']} - {r['ospite']}",
            "1/X/2 Poisson": " / ".join(pct(r.get(f"{k} P")) for k in ("1", "X", "2")),
            "1/X/2 Dixon–Coles": " / ".join(pct(r.get(f"{k} DC")) for k in ("1", "X", "2")),
            "Stato": r["stato"], "Risultato": r["risultato"], "Batch": r["batch"],
        })
    return pd.DataFrame(out)


def _aggiorna_risultati(db, forza=False):
    """Abbina i risultati alle previsioni (non tocca mai le previsioni). Al massimo ogni 10 minuti."""
    chiave = f"tp_agg_{db}"
    ultimo = st.session_state.get(chiave, 0)
    if not forza and time.time() - ultimo < 600:
        return st.session_state.get(chiave + "_esito")
    tot = {"liquidate": 0, "ambigue": 0, "rinviate": 0, "conflitti": 0}
    problemi = []
    for camp, stag in DB.coppie_da_liquidare(db):
        d = carica_dati_campionato(camp, stag)
        if d.get("stato") in (ERRORE, VUOTO) or not d.get("matches"):
            problemi.append(f"{camp} {stag}: dati non disponibili, risultati non aggiornati.")
            continue
        o = DB.liquida(db, camp, stag, d["matches"])
        for k in tot:
            tot[k] += o.get(k, 0)
        if d.get("stato") == OBSOLETO:
            problemi.append(f"{camp} {stag}: uso gli ultimi dati validi, non aggiornati.")
    st.session_state[chiave] = time.time()
    if any(tot.values()) and str(db) == str(DB.percorso_db(prova=False)):
        ok, msg = backup_remoto.sincronizza("previsioni.db")
        if not ok and backup_remoto.configurazione():
            problemi.append(f"Copia remota dell'archivio: {msg}")
    st.session_state[chiave + "_esito"] = (tot, problemi)
    return tot, problemi


# ------------------------------------------------------------------
# Sezioni
# ------------------------------------------------------------------


def _sezione_registra(db, prova):
    st.markdown("**1. Scegli il perimetro**")
    c1, c2 = st.columns(2)
    with c1:
        camp = st.selectbox(
            "Campionato", campionati_disponibili,
            index=campionati_disponibili.index(torneo_corrente()) if torneo_corrente() in campionati_disponibili else 0,
            key="tp_camp",
        )
    with c2:
        stag = st.selectbox(
            "Stagione", STAGIONI,
            index=STAGIONI.index(stagione_corrente()) if stagione_corrente() in STAGIONI else 0,
            key="tp_stag",
        )
    oggi = adesso().date()
    c3, c4 = st.columns(2)
    with c3:
        da = st.date_input("Dal", value=oggi, key="tp_da")
    with c4:
        a = st.date_input("Al", value=oggi + timedelta(days=4), key="tp_a")
    if a < da:
        st.error("La data finale è prima di quella iniziale.")
        return
    st.caption(
        "Le partite che giocano OGGI vengono escluse (non si può garantire che la previsione sia "
        "prima del fischio d'inizio). Per includere le gare di venerdì, registra giovedì."
    )

    d = carica_dati_campionato(camp, stag)
    if d.get("stato") in (ERRORE, VUOTO) or not d.get("matches"):
        st.error(d.get("messaggio") or "Dati non disponibili: non posso calcolare l'anteprima.")
        return
    dati_ok = d.get("stato") == OK
    if not dati_ok:
        st.warning(
            (d.get("messaggio") or "I dati non sono aggiornati.")
            + " Un batch registrato ora porterebbe l'etichetta «dati non aggiornati»."
        )

    df_stats = carica_stats_extra(camp, stag)
    adesso_dt = adesso()
    el, es = B.perimetro(d["matches"], da.isoformat(), a.isoformat(), adesso_dt)
    record, escl, cutoff, n_storico = B.calcola_batch(
        camp, stag, d["matches"], el, es, stato_dati=d.get("stato", OK), df_stats=df_stats
    )

    st.markdown("**2. Anteprima (non salva nulla)**")
    n_partite = len({r["match_key"] for r in record})
    m1, m2, m3 = st.columns(3)
    m1.metric("Partite", n_partite)
    m2.metric("Previsioni", len(record), help="Una per partita e per motore (Poisson e Dixon–Coles).")
    m3.metric("Escluse", len(escl))
    st.caption(f"Storico usato: {n_storico} partite giocate, fino al {cutoff or 'n.d.'}. Dati: {d.get('stato', OK)}.")

    if escl:
        conteggio = pd.Series([e["motivo"] for e in escl]).value_counts().rename_axis("Motivo").reset_index(name="Partite")
        st.dataframe(conteggio, use_container_width=True, hide_index=True)
        with st.expander(f"Elenco delle {len(escl)} escluse"):
            st.dataframe(pd.DataFrame(escl)[["descrizione", "motivo"]].rename(
                columns={"descrizione": "Partita", "motivo": "Motivo"}), use_container_width=True, hide_index=True)
    if n_partite:
        riga = {}
        for r in record:
            x = riga.setdefault(r["match_key"], {"Data": r["data_partita"], "Partita": f"{r['squadra_casa']} - {r['squadra_ospite']}"})
            if "errore" in r:
                x[r["motore"]] = "errore"
            else:
                x[r["motore"]] = " / ".join(pct(r[k]) for k in ("p1", "px", "p2"))
        anteprima = pd.DataFrame(riga.values()).rename(columns={"poisson": "1/X/2 Poisson", "dixon_coles": "1/X/2 Dixon–Coles"})
        st.dataframe(anteprima, use_container_width=True, hide_index=True)

    nomi = B.controlla_nomi({m["team1"] for m in el} | {m["team2"] for m in el}, df_stats)
    dubbi = [n for n in nomi if n["tipo"] != "esatto"]
    if dubbi:
        with st.expander(f"⚠️ {len(dubbi)} nomi squadra da controllare (tiri in porta)"):
            st.dataframe(pd.DataFrame(dubbi).rename(columns={"squadra": "Calendario", "associato": "Statistiche tiri", "tipo": "Abbinamento"}),
                         use_container_width=True, hide_index=True)
            st.caption("«approssimato» = trovato per somiglianza, da verificare a occhio; «assente» = per quella squadra i tiri non si usano.")

    st.markdown("**3. Registra**")
    if prova:
        st.info("Stai usando l'archivio di prova: quello che registri qui NON conta per il test.")
    ok_registra = True
    if not dati_ok:
        ok_registra = st.checkbox("Registra comunque, con i dati non aggiornati", key="tp_dati_non_ok")
    if n_partite == 0:
        st.info("Nessuna partita da registrare in questo perimetro.")
        return
    if st.button(f"📌 Registra batch ({n_partite} partite × 2 motori)", disabled=not ok_registra, key="tp_registra",
                 use_container_width=True):
        meta = {
            "campionato": camp, "stagione": stag, "da_data": da.isoformat(), "a_data": a.isoformat(),
            "versione_app": B.VERSIONE_APP, "stato_dati": d.get("stato", OK), "cutoff_dati": cutoff,
            "n_eleggibili": len(el),
            "note": f"nomi da controllare: {len(dubbi)}" if dubbi else None,
        }
        try:
            esito = DB.registra_batch(db, meta, record, escl)
        except Exception as e:  # noqa: BLE001
            st.error(f"Registrazione NON riuscita, nessun dato scritto: {type(e).__name__}: {e}")
            return
        if esito["batch_id"] is None:
            st.info(f"Niente di nuovo: tutte le {esito['duplicate']} previsioni erano già registrate con questo contenuto.")
        else:
            st.success(
                f"Batch {esito['batch_id']} registrato: {esito['nuove']} previsioni "
                f"({esito['fallite']} fallite, {esito['invalide']} non valide), "
                f"{len(escl)} partite escluse."
            )
            st.caption(f"Archivio: {db}")
            if prova:
                st.warning("Archivio di prova: non viene copiato in remoto. Scarica il backup dalla scheda «Archivio» per provare il ripristino.")
            else:
                ok, msg = backup_remoto.sincronizza("previsioni.db", forza=True)
                if ok:
                    st.success(f"Copia remota: {msg}.")
                elif backup_remoto.configurazione():
                    st.error(f"Copia remota NON riuscita ({msg}). Scarica subito il backup dalla scheda «Archivio».")
                else:
                    st.warning("Backup remoto non configurato: scarica subito il backup (scheda «Archivio»). Se l'app si riavvia, senza copia perdi il batch.")


def _sezione_partite(db):
    esito = _aggiorna_risultati(db)
    if st.button("🔄 Aggiorna risultati", key="tp_agg_btn"):
        esito = _aggiorna_risultati(db, forza=True)
    if esito:
        tot, problemi = esito
        if tot["liquidate"] or tot["rinviate"] or tot["ambigue"]:
            st.caption(f"Ultimo aggiornamento: {tot['liquidate']} risultati abbinati, {tot['rinviate']} riprogrammate, {tot['ambigue']} ambigue.")
        for p in problemi:
            st.warning(p)
    righe = DB.elenco_partite(db)
    if not righe:
        st.info("Nessuna partita registrata. Vai alla scheda «Registra».")
        return
    st.dataframe(tabella_partite(righe), use_container_width=True, hide_index=True)
    conf = DB.info_archivio(db)["conteggi"]["risultati_conflitti"]
    if conf:
        st.error(f"{conf} risultati in conflitto con quello già liquidato: il valore originale resta, serve una decisione manuale.")


def _riga_metriche(nome, m):
    return {
        "Motore": nome, "Partite": m["n"], "Brier 1X2": round(m["modello"]["brier"], 4),
        "Log-loss 1X2": round(m["modello"]["logloss"], 4), "Esito più probabile azzeccato": pct(m["modello"]["acc"]),
        "Brier Over 2.5": round(m["modello"]["brier_over"], 4), "Brier Goal": round(m["modello"]["brier_goal"], 4),
    }


def _ci(x, cifre=4):
    if not x:
        return "n.d."
    if x["lo"] is None:
        return f"{x['media']:+.{cifre}f} (troppo pochi dati per l'intervallo)"
    return f"{x['media']:+.{cifre}f}  [{x['lo']:+.{cifre}f} ; {x['hi']:+.{cifre}f}]"


def _sezione_valutazione(db):
    v = DB.valuta(db)
    c = v["copertura"]
    if not c["partite_registrate"]:
        st.info("Niente da valutare: nessuna previsione registrata.")
        return
    a, b, c3 = st.columns(3)
    a.metric("Registrate", c["partite_registrate"])
    b.metric("Con risultato", c["liquidate"])
    c3.metric("In attesa", c["in_attesa"] + c["rinviate"] + c["ambigue"])
    st.caption(f"{c['batch']} batch · {c['escluse']} partite escluse · {c['previsioni_fallite_o_invalide']} previsioni fallite o non valide.")
    conf = v["confronto"]
    if not conf:
        st.info("Non ci sono ancora partite concluse con previsione valida di entrambi i motori.")
        return
    n = conf["n"]
    if n < 30:
        st.warning(f"Solo {n} partite concluse: questo è un collaudo tecnico, non una misura della qualità del modello.")
    st.markdown(f"**Stesse {n} partite, due motori**")
    st.dataframe(pd.DataFrame([_riga_metriche("Poisson", conf["poisson"]), _riga_metriche("Dixon–Coles", conf["dixon_coles"])]),
                 use_container_width=True, hide_index=True)
    rif = conf["poisson"]["riferimento"]
    if rif:
        st.caption(
            f"Riferimento (frequenze storiche note al momento della previsione): Brier 1X2 {rif['brier']:.4f}, log-loss {rif['logloss']:.4f}. "
            "Più basso = meglio."
        )
    st.markdown("**Dixon–Coles meno Poisson, partita per partita**")
    st.write(f"Brier 1X2: {_ci(conf['delta_brier'])}")
    st.write(f"Log-loss 1X2: {_ci(conf['delta_logloss'])}")
    st.caption(
        "Valori negativi = Dixon–Coles ha un errore più basso. Se l'intervallo contiene lo zero, la differenza "
        "non si distingue dal caso. L'intervallo è approssimato e le partite della stessa giornata non sono "
        "del tutto indipendenti."
    )
    with st.expander("Calibrazione: probabilità prevista contro frequenza reale (1X2)"):
        for nome, chiave in (("Poisson", "poisson"), ("Dixon–Coles", "dixon_coles")):
            cal = conf[chiave]["calibrazione_1x2"]
            e = DB.ece(cal)
            st.markdown(f"*{nome}*" + (f" · errore di calibrazione {e * 100:.1f} punti" if e is not None else ""))
            st.dataframe(pd.DataFrame([{
                "Fascia": f"{r['da'] * 100:.0f}-{r['a'] * 100:.0f}%", "Casi": r["n"],
                "Prevista": pct(r["prob_media"]), "Reale": pct(r["freq_reale"]),
            } for r in cal]), use_container_width=True, hide_index=True)
        st.caption("Con pochi casi per fascia le differenze sono rumore: guarda sempre la colonna «Casi».")


def _sezione_monitoraggio(db):
    oggi = adesso().strftime("%Y-%m-%d")
    mon = DB.monitoraggio(db, oggi)
    if DB.ambiente()[0] == "streamlit_cloud" and not backup_remoto.configurazione():
        mon["segnali"].insert(0, ("errore", "Copia remota non configurata su Streamlit Cloud: se l'app si riavvia, i dati sul disco vanno persi."))
    for nome, e in backup_remoto.stato()["esiti"].items():
        if not e["ok"]:
            mon["segnali"].append(("errore", f"Copia remota di {nome}: {e['messaggio']}"))
    if not mon["segnali"]:
        st.success("Nessun segnale da controllare.")
    for livello, testo in mon["segnali"]:
        {"errore": st.error, "avviso": st.warning}.get(livello, st.info)(testo)
    righe = []
    for g, per_motore in mon["finestre"].items():
        for motore, m in per_motore.items():
            righe.append({
                "Finestra": f"ultimi {g} giorni", "Motore": B.NOMI_MOTORE.get(motore, motore), "Partite": m["n"],
                "Brier": round(m["brier"], 4), "Log-loss": round(m["logloss"], 4),
                "Errore calibrazione": "" if m["ece"] is None else f"{m['ece'] * 100:.1f}",
                "Brier riferimento": "" if m["brier_rif"] is None else round(m["brier_rif"], 4),
            })
    if righe:
        st.markdown("**Andamento nel tempo**")
        st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)
        st.caption("Servono per accorgersi di un peggioramento graduale. Con poche partite per finestra le variazioni sono casuali.")
    else:
        st.caption("L'andamento compare quando ci sono partite concluse con previsione registrata.")


def _sezione_backup_remoto(db, prova):
    st.markdown("**Copia automatica su GitHub (repository privato)**")
    s = backup_remoto.stato()
    if not s["configurato"]:
        (st.warning if DB.ambiente()[0] == "streamlit_cloud" else st.info)(
            "Non configurata. Senza questa copia, quando l'app si riavvia (o va in pausa) i dati sul disco spariscono."
        )
        with st.expander("Come attivarla (5 minuti)"):
            st.markdown(backup_remoto.ISTRUZIONI)
        return
    nomi = {"previsioni.db": "Archivio previsioni", "stato.json": "Schedine e curve", "registro_pronostici.csv": "Registro pronostici"}
    for nome, etichetta in nomi.items():
        e = s["esiti"].get(nome)
        if e is None:
            st.caption(f"{etichetta}: nessun movimento in questa sessione.")
        else:
            (st.caption if e["ok"] else st.error)(f"{etichetta}: {e['messaggio']} ({e['quando']})")
    if prova:
        st.caption("L'archivio di prova non viene copiato in remoto.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔁 Sincronizza ora", key="tp_sync", use_container_width=True):
                for n in backup_remoto.NOMI:
                    ok, msg = backup_remoto.sincronizza(n, forza=True)
                    (st.success if ok else st.warning)(f"{nomi[n]}: {msg}")
        with c2:
            if st.button("⬇️ Ripristina dalla copia remota", key="tp_ripr_remoto", use_container_width=True):
                ok, msg = backup_remoto.ripristina_ora()
                (st.success if ok else st.warning)(msg)


def _sezione_archivio(db, prova):
    inf = DB.info_archivio(db)
    st.write(f"**Dove:** `{inf['percorso']}`")
    st.write(f"**Dimensione:** {inf['dimensione_byte'] / 1024:.0f} KB · {inf['conteggi']['previsioni']} previsioni, "
             f"{inf['conteggi']['batches']} batch, {inf['conteggi']['risultati']} risultati")
    st.write(f"**Ultimo backup scaricato:** {inf['ultimo_backup_utc'] or 'mai'}")
    (st.warning if inf["ambiente"] in ("streamlit_cloud", "codespaces") else st.info)(inf["avviso_ambiente"])
    st.caption(
        "Stima di spazio: circa 0,75 KB per previsione, cioè circa 1,5 KB per partita con i due motori. "
        "Una stagione intera di un campionato (380 partite) pesa circa mezzo megabyte."
    )
    st.download_button(
        "⬇️ Scarica il backup completo (.db)", DB.backup_bytes(db),
        file_name=f"b-betting_previsioni_{adesso().strftime('%Y%m%d-%H%M')}{'_PROVA' if prova else ''}.db",
        mime="application/octet-stream", key="tp_backup", use_container_width=True,
        on_click=DB.segna_backup, kwargs={"db": db},
    )
    st.download_button(
        "⬇️ Esporta in CSV (leggibile)", DB.esporta_csv(db),
        file_name=f"b-betting_previsioni_{adesso().strftime('%Y%m%d-%H%M')}.csv",
        mime="text/csv", key="tp_csv", use_container_width=True,
    )
    _sezione_backup_remoto(db, prova)
    st.markdown("**Ripristina da un backup**")
    st.caption("Unisce il backup nell'archivio attuale: non cancella e non sovrascrive niente. Serve dopo un riavvio che ha azzerato il disco.")
    f = st.file_uploader("File di backup (.db)", type=["db"], key="tp_upload")
    if f is not None and st.button("Unisci questo backup", key="tp_unisci"):
        try:
            agg = DB.unisci_backup(db, f.getvalue())
            st.success(
                f"Backup unito: {agg['previsioni']} previsioni, {agg['batches']} batch e {agg['risultati']} risultati aggiunti"
                + (f"; {agg['risultati_completati']} risultati completati." if agg.get("risultati_completati") else ".")
            )
        except ValueError as e:
            st.error(f"Backup non valido, non ho cambiato nulla: {e}")
        except Exception as e:  # noqa: BLE001
            st.error(f"Ripristino non riuscito, nessuna modifica: {type(e).__name__}: {e}")


# ------------------------------------------------------------------
# Pagina
# ------------------------------------------------------------------


def mostra_test_previsioni():
    st.subheader("🧪 Test previsioni: Poisson e Dixon–Coles")
    st.caption(
        "Registra TUTTE le partite di un perimetro, con i due motori sugli stessi dati, prima che si giochino. "
        "Dopo i risultati misura quanto le probabilità erano giuste. Nessuna puntata, nessun ROI: è un test sulle "
        "probabilità. Le previsioni registrate non si possono modificare."
    )
    prova = st.checkbox("Archivio di prova (per collaudare, non conta per il test)", key="tp_prova")
    db = DB.percorso_db(prova=prova)
    t1, t2, t3, t4, t5 = st.tabs(["📌 Registra", "📋 Partite", "📊 Valutazione", "🩺 Monitoraggio", "💾 Archivio"])
    with t1:
        with sezione_sicura("Registra batch"):
            _sezione_registra(db, prova)
    with t2:
        with sezione_sicura("Partite registrate"):
            _sezione_partite(db)
    with t3:
        with sezione_sicura("Valutazione"):
            _sezione_valutazione(db)
    with t4:
        with sezione_sicura("Monitoraggio"):
            _sezione_monitoraggio(db)
    with t5:
        with sezione_sicura("Archivio"):
            _sezione_archivio(db, prova)
