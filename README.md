# Raccolta di order book per ricerca

Raccoglitore indipendente di dati pubblici **Kraken Futures linear perpetual USD**.
Nessuna chiave exchange, ordine o strategia di trading: soltanto GET pubbliche
di instruments e orderbook. L'adattatore Binance iniziale rimane disponibile
separatamente in `collector.py`, ma non è usato dal workflow corrente.
Preparato il 14 ottobre 2026. Stato e verifica dell'avvio in `AVVIO.md`.

## Raccolta

- 12 asset: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, LINK, LTC, DOT e TRX contro **USD**.
- Contratti `PF_XBTUSD`, `PF_ETHUSD`, `PF_SOLUSD`, `PF_BNBUSD`, `PF_XRPUSD`,
  `PF_ADAUSD`, `PF_DOGEUSD`, `PF_AVAXUSD`, `PF_LINKUSD`, `PF_LTCUSD`, `PF_DOTUSD`, `PF_TRXUSD`.
- Un'istantanea per contratto a ogni esecuzione: book REST completo conservato
  nel raw, ordinato e normalizzato ai migliori 100 livelli bid e ask per le metriche.
- Nessuno schedule interno GitHub: disattivato su richiesta dell'utente.
  Ogni avvio manuale o via API raccoglie un batch e termina.
- Raw book, metadati contratto, `serverTime`, tempi locali, latenza e stima offset
  dell'orologio; mid, spread e imbalance per controvalore USD nelle bande 5/10/25 bps.
- Ogni banda indica se la profondità restituita ne copre entrambi gli estremi.
  Una banda troncata non misura tutta la liquidità presente entro quella distanza.
- Livelli non finiti, non positivi, disordinati, book incrociati e timestamp
  incoerenti o troppo vecchi vengono registrati come errori, non come dati validi.

Gli snapshot dei contratti sono sequenziali, non simultanei. Gli orari effettivi
vanno usati nell'analisi: GitHub può ritardare o saltare esecuzioni. Il REST Kraken
qui usato non fornisce la data di ultimo aggiornamento del book: `serverTime`
è tempo di risposta del server, non età dell'ultimo evento. `book_update_ms=null`
e `book_update_time_available=false` rendono esplicita questa lacuna.
L'imbalance è una misura osservata, non una probabilità che il prezzo salga.

Il campo `symbol` conserva l'identificatore della watchlist di ricerca (es.
BTCUSDT), ma **non identifica il mercato osservato**: `source_symbol`, `venue`,
`quote_currency`, `instrument` e `symbol_role` indicano il contratto effettivo.
I risultati delle versioni Bot9 rimangono basati su Binance: questi nuovi dati
non sono un book Binance equivalente e non dimostrano miglioramenti della V3.
Prima di usarli come conferma cross-exchange servirà una verifica specifica.
Si accettano soltanto contratti flexible_futures con quote USD, contractSize1,
base corretta, tradeable e non suspended; se cambiano, si registra un errore.

## Conservazione

Ogni batch è un JSON gzip immutabile con versione dello schema (**2 per Kraken,
1 per i vecchi batch Binance**), codice sorgente,
metadati e record validi/errori. I batch con almeno un campione valido vanno nelle
release giornaliere `orderbook-YYYY-MM-DD`, insieme a checksum SHA256.
I batch parziali sono conservati e il workflow segnala comunque un fallimento.
I batch senza dati validi restano negli artifact diagnostici, conservati 30 giorni.
I dati non sono aggiunti alla cronologia Git a ogni esecuzione.

Le release non hanno la scadenza automatica degli artifact di Actions; il
repository o i file possono comunque essere cancellati, quindi è opportuno
scaricare copie esterne. Un giorno di 96 esecuzioni produce fino a 192 asset
(batch e checksum), entro il limite corrente di 1000 asset per release.

## Avvio e pausa

1. Actions → Collect public order book → Run workflow: esecuzione manuale finita.
2. Verificare successo, `status.json` con valid=12 e presenza della release.
3. Per pianificare dall'esterno, seguire [CRON_ESTERNO.md](CRON_ESTERNO.md).
4. Per sospendere la raccolta esterna, disattivare il servizio cron o il workflow.

Lo schedule GitHub è stato rimosso. Il cron esterno non è ancora configurato;
lo stato aggiornato è in `AVVIO.md`. Non occorre tenere acceso il PC.
`GITHUB_TOKEN` è fornito da Actions per caricare dati in questo repository;
non è una credenziale di trading. Nessun secret Binance va configurato.

Un cron esterno invia richieste a orari scelti, ma il job viene comunque
eseguito su un runner GitHub e può attendere in coda. Verificare gli orari
effettivi e la continuità dei dati, senza assumere una cadenza garantita.
Un nuovo account o un nome generico non elimina limiti e visibilità pubblica.

## Prove locali finite

Python 3.12 o successivo, solo libreria standard:

```powershell
python -B -m unittest -v
python -B kraken_collector.py --output output
```

Il primo comando usa soltanto dati sintetici. Il secondo fa un batch e termina.
Un HTTP403/451 impedisce la raccolta da quella rete. Non c'è un fallback
automatico fra exchange: la scelta Kraken è stata esplicitamente richiesta
dopo il blocco Binance e documentata. Una sorgente bloccata produce errori,
non viene sostituita silenziosamente né raggiunta tramite aggiramenti.

## Limiti della ricerca

Questa raccolta osserva il book ogni15minuti: non ricostruisce cancellazioni,
ordini e scambi fra due snapshot, non misura l'order-flow imbalance continuo
e non identifica spoofing. Per questi studi serve streaming con sequenze e
ricostruzione del book, su un servizio persistente. Non promette un aumento
di profitto del bot; serviranno campioni maturati, allineamento causale ai
segnali e verifica con costi, separando selezione e valutazione.

Non abbiamo order book nelle nostre cache OHLCV. Esistono fornitori/archivi
specializzati di book storico: "nessun exchange lo fornisce mai" non è una
regola universale. Qui costruiamo una storia nuova, non inventiamo quella passata.

Fonti ufficiali consultate il 14 ottobre 2026:
- [Kraken Futures book](https://docs.kraken.com/api-reference/market-data/get-orderbook)
- [Kraken strumenti](https://docs.kraken.com/api-reference/instrument-details/get-instruments)
- [Binance Order Book](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book)
- [GitHub schedule e inattività](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Quote release](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
- [Costi Actions](https://docs.github.com/en/actions/concepts/billing-and-usage)
