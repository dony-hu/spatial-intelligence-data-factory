.PHONY: up down test-integration report install-opencode factory-cli test-e2e

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

install-opencode:
	scripts/install_opencode.sh

factory-cli:
	.venv/bin/python scripts/factory_cli.py --help

test-e2e:
	.venv/bin/python scripts/test_end_to_end.py

