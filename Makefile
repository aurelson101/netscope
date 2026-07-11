.PHONY: up down logs test lint migrate
up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f
test:
	cd backend && pytest -q
lint:
	cd frontend && npm run build
smoke:
	python3 scripts/smoke_all.py --password "$${ADMIN_PASSWORD:-NetScopeAdmin2026!}"
migrate:
	docker compose exec backend-api python -c "import asyncio; from app.db.init import init_db; asyncio.run(init_db())"
