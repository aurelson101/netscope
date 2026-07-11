# Journaux NetScope

Les journaux persistants sont séparés par service :

- `api/netscope-api.log` : requêtes, latences et erreurs FastAPI ;
- `worker/netscope-worker.log` : tâches générales ;
- `scanner/netscope-scanner.log` : exécution des scans ;
- `scheduler/netscope-scheduler.log` : planificateur Celery ;
- `frontend/access.log` et `frontend/error.log` : Nginx ;
- `reports/` : rapports des simulations automatisées.

Les fichiers applicatifs utilisent JSON Lines et une rotation de 10 Mio avec cinq archives. Ne placez jamais de secrets dans les messages de log.
