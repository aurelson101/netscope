# Développement

Backend local : `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`.

Frontend local : `cd frontend && npm install && npm run dev`.

Par défaut, le backend local emploie SQLite. La stack Compose utilise PostgreSQL et Redis. Les tests n’exécutent aucun scan réseau vivant.
