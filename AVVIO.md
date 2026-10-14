# Verifica dell'avvio

**Stato attuale: schedule GitHub disattivato su richiesta dell'utente il
14 ottobre 2026. Rimane soltanto `workflow_dispatch`, manuale o da cron
esterno. `ORDERBOOK_ENABLED=false`; la variabile non serve più al workflow.
Il test da cron-job.org è riuscito; la ricorrenza automatica futura non è
ancora stata verificata.**

14 ottobre 2026. Repository: `harshvir05/Prova`.

- Accesso GitHub verificato come proprietario del repository.
- Sei test offline superati.
- Prova locale finita: 12 snapshot validi su12, batch gzip di17406byte.
- Pianificazione inizialmente disattivata mediante `ORDERBOOK_ENABLED=false`.
- Run manuale GitHub completato:
  https://github.com/harshvir05/Prova/actions/runs/38550733899
- Test offline sul runner superati. Binance `/fapi/v1/time` risponde HTTP451:
  nessuno snapshot raccolto (0/12), nessun dato inventato o exchange sostituito.
- Il workflow segnala correttamente il fallimento e conserva i diagnostici
  negli artifact. Il caricamento nelle release non è stato verificato su
  GitHub: non c'erano campioni validi da archiviare.
- `ORDERBOOK_ENABLED` rimane **false**. Nessuna raccolta periodica attiva.
- Le istruzioni per verificare e attivare un successivo ambiente funzionante
  restano nel README. La gratuità dei runner non elimina il blocco API.

Questa configurazione non riavvia il paper V3 sospeso sul PC.

## Cambio sorgente richiesto dall'utente

14 ottobre 2026: aggiunto adattatore esplicito Kraken Futures, schema2,
contratti linear perpetual USD per tutti i12 asset. Gli11 test offline
passano; la prova locale finita ha raccolto12/12 snapshot validi (59190byte).
Binance rimane una prova storica fallita, non una sorgente mescolata a Kraken.
La pianificazione resta spenta fino alla verifica manuale dell'adattatore
Kraken e del caricamento nelle release sul runner GitHub.

## Prova Kraken riuscita e attivazione

- Run: https://github.com/harshvir05/Prova/actions/runs/38551598812
- Esito: success,11 test superati,12 snapshot validi su12.
- Primi dati: https://github.com/harshvir05/Prova/releases/tag/orderbook-2026-10-14
- Batch gzip58187byte, checksum verificato dopo averlo scaricato dalla release.
- Verificati schema2, venuekraken e quoteUSD su tutti i12 record.
- Pianificazione abilitata: minuti UTC7,22,37,52, con possibili ritardi GitHub.
- Il primo batch è manuale: l'attivazione non dimostra ancora continuità nei
  mesi futuri. Controllare salti, errori, eventuale disattivazione per inattività
  e mantenere copie esterne dei dati.
- Il bot trading e le versioni ufficiali V1/V2/V3 non vengono modificati.

## Test da cron-job.org riuscito

14 ottobre 2026, ore13:01 italiane. L'utente ha avviato il test del job
"Prova - raccolta dati": GitHub ha risposto200 e creato il run38553637656.
Il job GitHub è partito alle11:01:22UTC e terminato con successo alle11:01:33UTC.
Il batch contiene12/12 snapshot Kraken validi ed è stato scaricato dalla
release per verificarne il checksum. Questo dimostra il percorso cron→GitHub→dati,
non ancora la continuità di tutte le future esecuzioni automatiche.
Il cron deve essere salvato e abilitato con frequenza15minuti nel servizio esterno.
Il token indicato dalla risposta GitHub scade il12gennaio2027 e va rinnovato
nelle impostazioni del cron prima della scadenza, senza pubblicarlo.

Run: https://github.com/harshvir05/Prova/actions/runs/38553637656

## Sospensione dello schedule interno richiesta dall'utente

La variabile è stata prima impostata a false, quindi è stato eliminato
il trigger schedule dal workflow. Nessuna esecuzione era in corso al controllo.
I primi batch e la prova riuscita restano conservati. L'avvio manuale resta
disponibile per il futuro cron esterno; [istruzioni](CRON_ESTERNO.md).
