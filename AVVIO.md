# Verifica dell'avvio

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
