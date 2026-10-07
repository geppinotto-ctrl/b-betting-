# Piano del test previsioni, fine settimana del 9 ottobre 2026

Versione congelata: **b-betting 0.3.0**, configurazione `CONFIG_ID` riportata in ogni previsione.
Nessuna modifica al modello, ai pesi o ai parametri finché dura il test. Una modifica = nuova versione = nuova serie, mai riscrittura.

## Cosa è e cosa non è
- È un **test tecnico**: verifica che registrazione, salvataggio, recupero e abbinamento dei risultati funzionino.
- **Non** dice se il modello è bravo: un weekend sono poche partite. La valutazione statistica richiede mesi.
- Nessuna puntata, nessun ROI, nessuno stake. Solo probabilità.

## Perimetro
- **Un solo campionato** (consiglio: Serie A), tutte le partite da venerdì a lunedì.
- Si registrano **tutte**, anche quelle con poco storico o poco interessanti. Il Top 10 non c'entra.
- Due motori sulle stesse partite: Poisson e Dixon–Coles (rho fisso -0.10).
- Configurazione: forma d=0.95, tiri in porta peso 0.3 (si usano solo le partite di giorni **precedenti** alla registrazione), assenze manuali spente, nessuna calibrazione.

## Cronologia
| Quando | Cosa |
|---|---|
| **Martedì 6 – Mercoledì 7** | Carica i file nel repository. Attiva la **copia automatica su GitHub** (sezione sotto): senza, su Streamlit Cloud i dati spariscono ai riavvii. |
| Mer 7 – Gio 8 | **Prova**: spunta «Archivio di prova», registra un batch, scarica il backup. Poi, dalla pagina dell'app su Streamlit: ⋮ → Reboot app. Controlla che schedine e registro tornino da soli (l'archivio di prova non viene copiato in remoto: per quello prova «Unisci backup»). |
| **Giovedì 8, sera** | **Registra il batch vero** (togli la spunta «Archivio di prova»): Dal = venerdì 9, Al = lunedì 12. Deve comparire «Copia remota: copia remota aggiornata». Scarica comunque anche il backup sul telefono. |
| Venerdì 9 | Non registrare partite di venerdì da venerdì: le gare di «oggi» vengono escluse di proposito. |
| Lun 12 – Mar 13 | Apri «Test previsioni». I risultati si abbinano da soli. Guarda «Monitoraggio». Scarica un altro backup. |

## Dove salva (l'app gira su Streamlit Community Cloud)
- Sul disco: `previsioni.db` (test), `stato.json` (schedine e curve), `registro_pronostici.csv`. **Il disco si azzera quando l'app si riavvia o va in pausa.**
- Per questo c'è la **copia automatica su un repository GitHub privato** (`backup_remoto.py`):
  - archivio previsioni: dopo ogni batch e dopo ogni aggiornamento risultati. Prima di caricare scarica la copia remota e la **unisce** (mai sovrascrivere alla cieca);
  - schedine/curve e registro: dopo ogni salvataggio, con una pausa di 2 minuti tra un caricamento e l'altro. Le ultime modifiche possono restare indietro fino a 2 minuti: il pulsante «Sincronizza ora» le carica subito;
  - dopo un riavvio i file mancanti tornano da soli all'apertura dell'app.
- **Regole di sicurezza della copia** (dai report di revisione):
  - archivio previsioni: se due sessioni scrivono insieme, l'app scarica la copia nuova, la **unisce** e ricarica; mai lo stesso file con un SHA aggiornato;
  - schedine/curve e registro: **una sola sessione alla volta**. Se la copia su GitHub è cambiata da un'altra sessione, l'app **non sovrascrive** e mostra un errore;
  - un file locale illeggibile viene messo da parte (mai cancellato) e non viene mai caricato al posto di una copia buona;
  - dopo ogni caricamento si controlla che GitHub abbia salvato **esattamente** i byte inviati;
  - il pulsante **«Verifica la copia su GitHub»** (scheda Archivio) dice, per ogni file, quando è stata l'ultima copia confermata e se è allineata ai dati locali.
- Un upload riuscito non è un backup verificato, e un backup verificato non è un ripristino riuscito: l'unica prova completa è un ripristino. Lo facciamo giovedì sera, dopo il primo batch vero.
- Il backup manuale (pulsante nella scheda «Archivio») resta il secondo paracadute. Scaricalo dopo il batch.
- Il token ha una scadenza: quando scade la copia si ferma e l'app lo segnala in rosso nella scheda «Monitoraggio».
- I dati stanno su GitHub (servizio esterno) in un repository privato tuo. Mai caricarli nel repository pubblico dell'app: metti nel suo `.gitignore` `dati_utente/`, `registro_pronostici.csv`, `*.corrotto*`, `__pycache__/`.

### Attivare la copia remota (5 minuti)
1. Su GitHub crea un repository **privato** (es. `b-betting-dati`) con un file README.
2. GitHub → Settings → Developer settings → Fine-grained tokens → Generate new token. Repository access: **solo** `b-betting-dati`. Permissions → Repository → **Contents: Read and write**. Scadenza: la più lunga consentita.
3. Su Streamlit Community Cloud: la tua app → ⋮ → Settings → **Secrets**, incolla (con i tuoi valori):
```
GITHUB_BACKUP_TOKEN = "github_pat_..."
GITHUB_BACKUP_REPO = "tuo-utente/b-betting-dati"
```
4. Riavvia l'app e apri «Test previsioni» → «Archivio»: la sezione «Copia automatica su GitHub» non deve più dire «Non configurata».

## Controlli prima di fidarsi
1. Dopo il batch: id batch, numero partite, numero escluse con motivo, percorso del file.
2. «Nomi da controllare»: guarda gli abbinamenti «approssimato» o «assente».
3. Dopo il riavvio: stesse previsioni, nessun duplicato.
4. Dopo le partite: tutte abbinate? Ambigue, riprogrammate o in conflitto vanno guardate a mano.

## Cosa NON fare
- Modificare il modello perché i risultati non piacciono.
- Registrare partite già iniziate come se fossero «prima».
- Giudicare il motore da un weekend.
- Usare come criteri ufficiali soglie come «500 partite» o «ECE sotto 0,05»: sono proposte da validare.

## Dopo il weekend
Fase B: stesso protocollo ogni settimana, versione congelata, report settimanale (copertura, anomalie, Brier e log-loss con intervalli). Prima di toccare il modello: un esperimento alla volta, confrontato sulle stesse partite.
