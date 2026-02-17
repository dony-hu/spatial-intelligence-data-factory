# dispatch-address-line-closure-001 Test Report

## Scope
- web_e2e_catalog: unknown -> executed result
- Address governance smoke regression: 10 samples
- Test panel readonly SQL: whitelist/security tests

## Commands and Results
1. `PYTHONPATH=. /Users/huda/Code/.venv/bin/pytest -q services/governance_api/tests/test_lab_sql_api.py`
- result: `2 passed in 0.29s`

2. `/Users/huda/Code/.venv/bin/python scripts/run_cn1300_module_coverage.py --limit 10`
- result: `rows=10`
- normalize hit rate: `0.6`
- parse field hit rate: `province=1.0 city=1.0 district=1.0 road=0.9 house_no=0.9`
- match hit rate: `0.7`
- score judgement hit rate: `1.0`

3. `/Users/huda/Code/.venv/bin/python scripts/run_web_e2e_catalog.py`
- result: `total=4 passed=2 failed=2 skipped=0 duration=42.07s`
- status: `failed`
- failing tests:
  - `tests/web_e2e/test_lab_replay_ui.py::test_lab_replay_page_renders_core_sections[chromium]`
  - `tests/web_e2e/test_lab_replay_ui.py::test_lab_replay_page_reflects_approval_and_activation_path[chromium]`
- error signature: `socket.timeout` in `tests/web_e2e/conftest.py` during `POST /v1/governance/lab/optimize/web-e2e-batch`

4. `PYTHONPATH=. /Users/huda/Code/.venv/bin/pytest -q services/governance_api/tests/test_lab_api.py services/governance_api/tests/test_lab_sql_api.py`
- result: `12 passed in 0.41s`

5. `/Users/huda/Code/.venv/bin/python scripts/build_dashboard_data.py`
- result: dashboard data regenerated (`dashboard_manifest/project_overview/test_status_board/worklines_overview/workpackages_live`)

6. `/Users/huda/Code/.venv/bin/python scripts/update_dashboard_on_event.py --event-type test_synced ...`
- result: test sync events appended for:
  - `wp-pm-dashboard-test-progress-v0.1.0`
  - `wp-test-panel-sql-query-readonly-v0.1.0`

## Failure Localization and Retry Suggestions
- Localization
  - Timeout source: `./tests/web_e2e/conftest.py` (`_http_post(..., timeout=10)`)
  - Endpoint under pressure: `/v1/governance/lab/optimize/web-e2e-batch`
- Retry suggestions
  1. Increase optimize call timeout to `30s` in `tests/web_e2e/conftest.py`.
  2. Add preflight health check before optimize call (ops summary/health endpoint).
  3. Optional: add one retry with short backoff for optimize fixture setup.
  4. Retry command: `/Users/huda/Code/.venv/bin/python scripts/run_web_e2e_catalog.py`

## Nightly Integration Suggestion
- Nightly chain:
  1. `/Users/huda/Code/.venv/bin/python scripts/run_web_e2e_catalog.py`
  2. `/Users/huda/Code/.venv/bin/python scripts/run_cn1300_module_coverage.py --limit 10`
  3. `/Users/huda/Code/.venv/bin/python scripts/update_dashboard_on_event.py --event-type test_synced --workpackage-id wp-pm-dashboard-test-progress-v0.1.0 --summary "nightly test sync" --operator "nightly-bot" --payload-json '{"suite_id":"suite_web_e2e_catalog"}'`
- Gate policy:
  - web_e2e failed > 0 => `NO_GO`
  - SQL readonly security tests failed > 0 => `NO_GO`
