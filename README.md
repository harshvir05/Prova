# Raccolta di order book per ricerca

Raccoglitore indipendente di dati pubblici Binance USD-M perpetual. Nessuna
chiave exchange, ordine o strategia di trading: soltanto GET di time e depth.
Preparato il 14 ottobre 2026. Stato e verifica dell'avvio in `AVVIO.md`.

## Raccolta

- 12 coppie: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, AVAX, LINK, LTC, DOT e TRX contro USDT.
- Un'istantanea per coppia a ogni esecuzione, fino a 100 livelli bid e ask.
- Pianificazione indicativa ogni 15 minuti, ai minuti UTC 7, 22, 37 e 52.
- Raw book, update ID, tempi exchange E/T, tempi locali, latenza e stima offset
  dell'orologio; mid, spread e imbalance per controvalore nelle bande 5/10/25 bps.
- Ogni banda indica se la profondità restituita ne copre entrambi gli estremi.
  Una banda troncata non misura tutta la liquidità presente entro quella distanza.
- Livelli non finiti, non positivi, disordinati, book incrociati e timestamp
  incoerenti o troppo vecchi vengono registrati come errori, non come dati validi.

Gli snapshot delle coppie sono sequenziali, non simultanei. Gli orari effettivi
vanno usati nell'analisi: GitHub può ritardare o saltare esecuzioni. Il book
visibile non include gli ordini RPI, secondo la documentazione Binance.
L'imbalance è una misura osservata, non una probabilità che il prezzo salga.

## Conservazione

Ogni batch è un JSON gzip immutabile con versione dello schema, codice sorgente,
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
3. Settings → Secrets and variables → Actions → Variables: impostare
   `ORDERBOOK_ENABLED` a `true` soltanto dopo il controllo del primo run.
4. Per sospendere, impostarla a `false` o disabilitare il workflow.

La pianificazione è inizialmente spenta. Non occorre tenere acceso il PC.
`GITHUB_TOKEN` è fornito da Actions per caricare dati in questo repository;
non è una credenziale di trading. Nessun secret Binance va configurato.

In un repository pubblico GitHub può disabilitare gli schedule dopo 60 giorni
senza attività: controllare periodicamente il workflow e la continuità dei dati.
Un nuovo account o un nome generico non elimina limiti e visibilità pubblica.

## Prove locali finite

Python 3.12 o successivo, solo libreria standard:

```powershell
python -B -m unittest -v
python -B collector.py --output output
```

Il primo comando usa soltanto dati sintetici. Il secondo fa un batch e termina.
Un HTTP403/451 impedisce la raccolta da quella rete: non sostituiamo futures
con spot o un altro exchange, né aggiriamo il blocco. In tal caso la
pianificazione resta spenta e occorre una sorgente/infrastruttura accessibile.

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

Fonti ufficiali consultate il14ottobre2026:
- [Binance Order Book](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book)
- [GitHub schedule e inattività](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Quote release](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
- [Costi Actions](https://docs.github.com/en/actions/concepts/billing-and-usage)
