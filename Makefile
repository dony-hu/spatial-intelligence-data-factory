.PHONY: up down test-integration report

up:
	docker compose up -d

down:
	docker compose down

test-integration:
	DATABASE_URL=postgresql://postgres:postgres@localhost:5432/spatial_db .venv/bin/python -m pytest tests/ services/ packages/

report:
	.venv/bin/python scripts/run_nightly_quality_gate.py

report-governance:
	DATABASE_URL=postgresql://postgres:postgres@localhost:5432/spatial_db KEEP_DB_DATA=1 .venv/bin/python scripts/collect_governance_metrics.py

