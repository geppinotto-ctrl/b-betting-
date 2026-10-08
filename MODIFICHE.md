# b-betting — modifiche di robustezza

## File nuovo
- **resilienza.py** — `http_get` (retry + backoff), `ErroreDati`, `valida_matches`,
  `sezione_sicura`, `calcolo_con_progresso`, `svuota_cache` (selettiva), registro stato dati.

## File modificati
| File | Cosa cambia |
|---|---|
| config.py | Lettura sicura dei secrets (non crasha senza `secrets.toml`). `ODDS_API_BASE` sovrascrivibile da secrets (default invariato: `https://odss-api.com/api/v1`). |
| dati.py | Download che fallisce = eccezione (non in cache) invece di `{"matches": []}` in cache 30 min. Fallback sull'ultimo dato buono, validazione partite, controllo che i dati siano della stagione richiesta, retry. Stati: ok / parziale / obsoleto / vuoto / errore. |
| quote.py | **Filtro ADM rigoroso (Manus):** in modalità ADM passano solo i bookmaker con `playable_it` esplicitamente vero, senza ripiego automatico su operatori non ADM; messaggio chiaro quando non ce ne sono. Inoltre: HTTP con retry; errori del test API non più in cache per 1 ora; messaggi per 401/403/404/429; scarto di quote NaN/inf/non numeriche e di bookmaker con esiti malformati; `ottieni_catalogo_partita` non solleva mai; spinner sul caricamento quote. |
| modello.py | `raccogli_consigli`: un torneo o una partita rotti non bloccano gli altri; il risultato parziale non finisce in cache. |
| analisi.py | Confronto modello/mercato senza filtro ADM (serve solo la probabilità implicita). Ogni tab isolato con `sezione_sicura`; spinner sul caricamento dati; avvisi di stato (dati obsoleti/parziali/errore); backtest con barra di progresso e controllo dati minimi. |
| calibra_modello.py, confronta_motori.py | Barra di progresso reale (per stagione e per partita); niente cache se i dati sono incompleti. Compatibili con l'uso da riga di comando. |
| assenze.py | Salvataggio CSV con gestione errori; CSV rovinato non ferma i pronostici; cache selettiva. |
| schedina.py | **(Manus)** Rimosso l'editor duplicato: la schedina veniva mostrata due volte, con doppio pulsante «Svuota» e doppio messaggio «schedina vuota». |
| home.py | Avviso esplicito invece dell'`except` silenzioso. |
| app.py | "Aggiorna Dati" e cambio motore puliscono solo ciò che serve (le quote API NON vengono cancellate, salvo spunta «Aggiorna anche le quote»). Passi decorativi (audio/sfondo) non bloccano l'avvio. Pagine pesanti isolate. |

## Rimosso
- `motore_probabilistico (1).py` (duplicato identico).

## Test: suite ufficiale (aggiornato 8 ottobre 2026)
La suite ufficiale sta nella cartella `tests/` **dell'ambiente di sviluppo**, non nel repository dell'app
(l'app non ne ha bisogno). Comando unico, dalla cartella del progetto:
`python tests/esegui_test.py`. Contiene 13 file `tests/test_*.py` e uno `streamlit` finto in
`tests/stubs/streamlit/`. L'esito completo e le impronte dei file sono in `RAPPORTO_TEST_2026-10-08.txt`.
I vecchi `t_*.py` alla radice del repository sono materiale **legacy** (la prima suite) e non sono la suite ufficiale.
Provano la logica con dati simulati: NON sostituiscono una prova nell'app Streamlit reale né su GitHub vero.

## Da verificare con l'API reale
Il filtro ADM rigoroso presuppone che il provider invii `playable_it`. Se in modalità ADM non compare nessuna quota ma disattivando il filtro sì, il campo manca.
Il dominio del provider si imposta con `ODDS_API_BASE` nei secrets (default attuale: `https://odss-api.com/api/v1`, da confermare).

## Registro pronostici (nuovo)
- **registro.py** (nuovo): salva le giocate PRIMA della partita, chiude gli esiti da solo con il risultato reale,
  mostra % di successo con intervallo di confidenza, Brier, resa simulata (solo giocate con quota) e calibrazione per fasce.
  Una giocata già registrata non si sovrascrive. Sotto 30 giocate chiuse l'app avverte che i numeri non sono significativi.
  File: `registro_pronostici.csv` accanto al codice (su servizi che azzerano il disco va scaricato con il pulsante CSV).
- **app.py**: pulsante «📒 Registro pronostici» nel menu laterale; la pagina è isolata con `sezione_sicura`.
- **analisi.py**: pulsante «📌 Registra le Top 10» in AI Advice.
- **radar.py**: pulsante «📌 Registra i segnali (con quota)» nel Radar.
- **modello.py**: i consigli includono `t1` e `t2` (squadre separate), necessari al registro.
- Test del registro: `tests/test_registro.py` (37 controlli).
