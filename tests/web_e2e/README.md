# Web UI E2E Test Framework

This folder contains browser-based E2E tests for governance Lab pages, including:
- Lab replay page (`/v1/governance/lab/change_requests/{id}/view`)
- Observability live page (`/v1/governance/lab/observability/view`)

## Scope

- Start Governance API locally (unless `WEB_E2E_BASE_URL` is provided).
- Create a Lab optimize run using API fixtures.
- Open Lab replay HTML view in Chromium.
- Verify key UI sections and approval gating behavior.
- Open Observability live HTML view in Chromium.
- Verify SSE-driven live connection state and core KPI sections.

## Install

```bash
pip install -r requirements-governance.txt -r requirements-web-e2e.txt
python -m playwright install chromium
```

## Run

```bash
pytest tests/web_e2e -q
```

## Run against existing server

```bash
export WEB_E2E_BASE_URL=http://127.0.0.1:8000
pytest tests/web_e2e -q
```
