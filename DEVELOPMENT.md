# Développer NetScope

Commencez par lire [l’architecture](docs/ARCHITECTURE.md). Elle explique les flux API, Celery, découverte et corrélation ainsi que les invariants à préserver.

## Environnement recommandé

- Python 3.13 ;
- Node.js 22 ;
- Docker Engine et Compose v2 ;
- PostgreSQL et Redis via Docker pour les tests d’intégration.

## Backend local

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Sans `DATABASE_URL`, le backend utilise SQLite. Redis reste nécessaire pour Celery et la limitation de connexion. Pour utiliser les services Compose :

```bash
docker compose up -d postgres redis
```

## Frontend local

```bash
cd frontend
npm ci
npm run dev
```

Vite écoute sur `http://localhost:5173`. Les appels `/api` doivent viser l’API ou passer par le proxy Compose selon l’environnement choisi.

## Migrations

```bash
cd backend
alembic upgrade head
alembic current
```

Pour créer une révision :

```bash
alembic revision -m "description courte"
```

Relisez toujours le SQL généré. Une migration doit fonctionner sur une base existante et sur une base vide, puis avoir un `downgrade` sûr.

## Tests et contrôles

```bash
cd backend
pytest

cd ../frontend
npm ci
npm run build
npm run test:e2e

cd ..
docker compose config -q
docker compose up -d --build
curl --fail http://localhost:8080/health
```

Les tests backend n’exécutent aucun scan vivant. Utilisez des fixtures pour les sorties Nmap/SNMP et des doubles pour Celery ou SMTP.

## Style de contribution

- gardez la logique métier testable hors des composants React lorsque cela apporte de la clarté ;
- ne lancez jamais une commande réseau via un shell construit dynamiquement ;
- validez les cibles avec les règles de sécurité existantes ;
- n’exposez aucun secret dans une réponse, un log, une fixture ou un commit ;
- ajoutez une migration pour toute évolution du modèle ;
- journalisez les actions administratives importantes dans `AuditLog` ;
- mettez à jour l’architecture lorsque vous ajoutez un composant ou modifiez un flux.

## Diagnostic rapide

```bash
docker compose ps
docker compose logs --tail=100 backend-api worker scheduler scanner
curl --fail http://localhost:8080/health
curl --fail http://localhost:8080/api/openapi.json
```

La sonde interne `/health/ready` vérifie PostgreSQL et Redis. La sonde `/health` reste une vérification de vie légère du processus API.
