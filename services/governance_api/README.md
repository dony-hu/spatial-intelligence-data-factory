# governance_api Runtime Baseline

- Python: `3.11+` (recommended `3.11.x`)
- Queue mode for local/API tests: in-memory fallback is enabled by default.

## Install

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-governance.txt
.venv/bin/pip install pytest
```

## Core Regression Commands

```bash
PYTHONPATH=. .venv/bin/pytest services/governance_api/tests/test_rulesets_api.py -q
PYTHONPATH=. .venv/bin/pytest services/governance_api/tests/test_ops_api.py -q
PYTHONPATH=. .venv/bin/pytest services/governance_api/tests/test_lab_api.py -q
PYTHONPATH=. .venv/bin/pytest services/governance_api/tests/test_observability_integration.py -q
```
