.PHONY: up down test lint build migrate
up:
	docker compose up --build

down:
	docker compose down

test:
	cd backend && python -m pytest -q

lint:
	cd backend && ruff check relayops tests
	cd frontend && npm run build

build:
	docker compose build

migrate:
	cd backend && alembic upgrade head
