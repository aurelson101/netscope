.PHONY: up down logs test lint migrate diagnose
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
	python3 scripts/smoke_all.py --username "$${ADMIN_EMAIL:-admin@netscope.local}" --password "$${ADMIN_PASSWORD:-NetScopeAdmin2026!}"
diagnose:
	./scripts/diagnose.sh
migrate:
	docker compose exec backend-api python -c "import asyncio; from app.db.init import init_db; asyncio.run(init_db())"
