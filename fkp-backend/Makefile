BREW_PREFIX := $(shell brew --prefix)
export DYLD_FALLBACK_LIBRARY_PATH := $(BREW_PREFIX)/lib

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

flush:
	@read -p "Hapus SEMUA data? Ketik 'yes' untuk lanjut: " ans; \
	[ "$$ans" = "yes" ] || { echo "Dibatalkan."; exit 1; }
	PYTHONPATH=. python scripts/flush_data.py

.PHONY: dev start test migrate makemigrations rollback rollback-all \
        migration-status migration-history flush fresh