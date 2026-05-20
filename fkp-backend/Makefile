dev:
	uvicorn app.main:app --reload

start:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

migrate:
	alembic upgrade head

makemigrations:
	@read -p "Migration message: " msg; alembic revision --autogenerate -m "$$msg"

rollback:
	alembic downgrade -1

rollback-all:
	alembic downgrade base

migration-status:
	alembic current

migration-history:
	alembic history