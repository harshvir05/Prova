# Avvio da cron esterno

Lo schedule interno GitHub è stato rimosso il14ottobre2026 su richiesta
dell'utente. Il workflow conserva soltanto `workflow_dispatch`. Il servizio
cron esterno è stato testato con successo il14ottobre2026 (run38553637656);
la ricorrenza futura deve ancora essere verificata. Queste sono le impostazioni.

## Richiesta HTTP

Metodo: **POST**

URL:

```text
https://api.github.com/repos/harshvir05/Prova/actions/workflows/collect.yml/dispatches
```

Headers:

```text
Accept: application/vnd.github+json
Authorization: Bearer TOKEN_PERSONALE
Content-Type: application/json
X-GitHub-Api-Version: 2026-03-10
```

Body JSON:

```json
{"ref":"main"}
```

Pianificazione suggerita sul servizio esterno: ogni15minuti. Il servizio
deve supportare POST, headers personalizzati e body JSON.

Usare un token fine-grained del nuovo account, limitato al repository
`Prova`, con permesso repository **Actions: Read and write**. La creazione
del token si effettua nelle impostazioni GitHub del proprio account;
salvarlo nel campo riservato del servizio cron, non nel repository o in chat.
La credenziale del cron avvia il workflow; l'upload dei dati utilizza poi
il GITHUB_TOKEN fornito da Actions, con i permessi già definiti nel workflow.

L'API accetta la richiesta di avvio: questo non prova che il job abbia
raccolto12campioni o salvato la release. Verificare anche l'esito in Actions
e i file nelle release. Non usare la variabile ORDERBOOK_ENABLED come pausa
del cron esterno: disattivare il cron o il workflow quando si vuole fermarlo.

## Precisione

Il cron esterno può rendere più regolare la richiesta di avvio. Rimangono
possibili attese del runner, tempi di rete e accodamento della concorrenza.
Questo non è un servizio real-time a cadenza esatta. Se serve puntualità
stretta nell'osservazione del book, occorre un processo su infrastruttura
persistente, non soltanto un trigger esterno di GitHub Actions.

Fonte ufficiale:
[Create a workflow dispatch event](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).
