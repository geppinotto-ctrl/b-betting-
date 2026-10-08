# Piano del test previsioni: documento UFFICIALE

Versione del documento: 2026-10-08, revisione 2. **Sostituisce** `PIANO_TEST_WEEKEND.md` e `PIANO_TEST_WEEKEND (1).md`, che vanno cancellati dal repository (la cronologia di GitHub ne conserva la traccia).

**Build congelata:** `b-betting 0.3.0`, configurazione `CONFIG_ID 624b0974`. Le impronte SHA-256 di ogni file della build sono in `MANIFEST_RILASCIO.txt`. Vale solo questa build: ogni modifica al codice è una nuova versione e va registrata.

## Cosa è e cosa non è
- È un **test tecnico di raccolta e conservazione**: verifica che registrazione, salvataggio, copia remota, recupero e abbinamento dei risultati funzionino.
- **Non** misura la qualità del modello: pochi giorni sono poche partite. La valutazione statistica richiede mesi.
- Nessuna puntata, nessun ROI.

## Perimetro
- Serie A, 2026-27, partite dall'8 al 13 ottobre. Le prime sono sabato 10: **si registra entro venerdì 9**. Le partite che giocano nel giorno stesso della registrazione vengono escluse di proposito.
- Si registrano **tutte** le partite, con due motori (Poisson e Dixon–Coles) sugli stessi dati.
- Configurazione: forma d=0.95, tiri in porta peso 0.3 (solo partite di giorni **precedenti**), assenze manuali spente, nessuna calibrazione, rho -0.10.

## Che livello di prova abbiamo, onestamente
| Cosa | Livello | Stato |
|---|---|---|
| Logica di backup: conflitti, file corrotti, manifest, verifica dei byte, ripristino | **Simulato** (GitHub finto), 90 controlli | Superati |
| Scrittura su GitHub reale e lettura dopo il riavvio | **Reale**, 6 ottobre, archivio vuoto o di prova | Fatto |
| Ripristino da file `.db` scaricato sul telefono | **Reale**, archivio di prova | Fatto |
| Ripristino automatico da GitHub con dati veri | **Reale** | **Da provare** dopo il primo batch |
| Conflitti su GitHub vero | — | Non provato (richiede due sessioni insieme) |

Un test simulato che passa **non** equivale a un test su GitHub vero. Nel report finale si dice sempre quale dei due è stato fatto.

## Quattro cose diverse (non confonderle)
1. **File caricato**: GitHub ha risposto e ha salvato esattamente i byte inviati.
2. **Manifest aggiornato**: il file `manifest.json` descrive quella copia. Se non si aggiorna, l'app mostra un avviso e **non** un successo.
3. **Copia verificata**: il pulsante «🔎 Verifica la copia su GitHub» **scarica** i file e controlla che siano validi, uguali al manifest e allineati ai dati locali.
4. **Ripristino riuscito**: i dati tornano davvero dopo un riavvio. È l'unica prova completa.

## Backup manuale: cosa contiene davvero
Non è uno snapshot unico. Sono export separati:
- **`.db`** (scheda Archivio): solo l'archivio previsioni del test;
- **CSV** (scheda Archivio): lettura comoda dello stesso archivio, non serve a ripristinare;
- **Schedine**: export dalla pagina Schedina;
- **Registro pronostici**: CSV dalla sua pagina.

**Ripristino completo** = riavvio dell'app con la copia automatica attiva (ripristina i tre file da GitHub) oppure, a mano, unire il `.db`, reimportare le schedine e il CSV del registro.
Il pulsante «Unisci archivio previsioni da GitHub» ripristina **solo** l'archivio previsioni.

## Esiti attesi (per non spaventarsi)
- **Archivio previsioni**: unico file che DEVE risultare «VERIFICATA» dopo il batch.
- **Schedine e curve** e **Registro pronostici**: finché non hai salvato nulla in quelle sezioni il file locale non esiste, quindi anche su GitHub non c'è. «niente da caricare» e «nessun file su GitHub» sono **normali, non applicabili**, e non contano come anomalia. Non creare dati finti per ottenere il verde. Quando salverai una schedina o una giocata nel registro, il file nascerà da solo e verrà copiato.
- **Partite di oggi**: il testo della pagina dice che sono escluse. La logica ne ammette una solo se l'orario è noto e mancano almeno 3 ore al calcio d'inizio. Per questo batch conta l'anteprima: leggi la lista delle escluse e il motivo. Il testo sarà allineato in una versione successiva (0.3.1, solo parole, non cambia i calcoli) dopo il weekend.

## Cronologia
| Quando | Cosa |
|---|---|
| Giovedì 8 mattina | Fatto: file caricati, piani vecchi cancellati, `.gitignore`, prima verifica della copia su GitHub (archivio vuoto: verificata). |
| **Giovedì 8 sera** | **Registrazione del batch**, con la procedura passo per passo che Claude ti scrive in chat. |
| Subito dopo il batch | «🔎 Verifica la copia su GitHub» deve dire VERIFICATA per l'archivio previsioni. Scarica il backup `.db` sul telefono e controlla che il file sia arrivato. |
| Dopo il batch | **Solo se** la verifica è verde e il `.db` è scaricato: Manage app → Reboot app, e controlla che l'archivio ritorni da solo (stessi conteggi). Se anche solo una riga è rossa, **non riavviare**: scrivi a Claude. |
| Lun 12 – Mar 13 | Apri «Test previsioni»: i risultati si abbinano da soli. Guarda «Monitoraggio». Scarica un altro backup. |

## Da annotare dopo il batch (evidenza)
- commit mostrato da GitHub sulla pagina del repository (le prime 7 cifre) e data/ora del deploy;
- `CONFIG_ID` (624b0974) e versione (0.3.0);
- id del batch, numero di partite, numero di escluse con motivo, previsioni per motore;
- esito della verifica remota per ciascuno dei tre file;
- se hai riavviato e cosa è tornato.
Mai annotare token o password.

## Regole
- Una sola sessione dell'app durante registrazione e sincronizzazione.
- Nessuna modifica al codice durante il test, salvo correzioni autorizzate e registrate (nuova versione e nuova serie).
- Se il test parte con un'anomalia non chiarita, si rinvia: la validità dell'evidenza viene prima della data.

## Sicurezza
- Repository dati privato, token solo sul repository dati e con permesso Contents; scadenza 06/10/2027.
- `.gitignore` consigliato nel repository dell'app: vedi `gitignore.txt`.
- Il token sta solo nei Secrets di Streamlit.
