from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from services.governance_api.app.main import app


def ensure_env(workspace_root: Path) -> None:
    os.environ.setdefault("AGENT_RUNTIME", "openhands")
    os.environ.setdefault("OPENHANDS_STRICT", "1")
    os.environ.setdefault("GOVERNANCE_QUEUE_MODE", "sync")
    config_path = workspace_root / "config" / "llm_api.json"
    os.environ.setdefault("LLM_CONFIG_PATH", str(config_path))


def main() -> int:
    workspace_root = Path(__file__).resolve().parents[1]
    ensure_env(workspace_root)

    client = TestClient(app)
    submit_payload = {
        "idempotency_key": "idem-e2e-real-001",
        "batch_name": "batch-e2e-real",
        "ruleset_id": "default",
        "records": [
            {"raw_id": "real-e2e-1", "raw_text": "深圳市南山区科技园南区科苑南路2666号"}
        ],
    }

    submit_resp = client.post("/v1/governance/tasks", json=submit_payload)
    if submit_resp.status_code != 200:
        print(json.dumps({"stage": "submit", "status_code": submit_resp.status_code, "body": submit_resp.text}, ensure_ascii=False))
        return 1

    task_id = submit_resp.json().get("task_id")
    status_resp = client.get(f"/v1/governance/tasks/{task_id}")
    result_resp = client.get(f"/v1/governance/tasks/{task_id}/result")
    if status_resp.status_code != 200 or result_resp.status_code != 200:
        print(json.dumps({"stage": "query", "task_id": task_id}, ensure_ascii=False))
        return 1

    status = status_resp.json().get("status")
    results = result_resp.json().get("results", [])
    if status != "SUCCEEDED" or not results:
        print(json.dumps({"stage": "execute", "task_id": task_id, "status": status, "results": results}, ensure_ascii=False))
        return 1

    review_resp = client.post(
        f"/v1/governance/reviews/{task_id}/decision",
        json={"raw_id": "real-e2e-1", "review_status": "approved", "reviewer": "e2e-user"},
    )
    if review_resp.status_code != 200:
        print(json.dumps({"stage": "review", "status_code": review_resp.status_code, "body": review_resp.text}, ensure_ascii=False))
        return 1

    ops_resp = client.get(f"/v1/governance/ops/summary?task_id={task_id}")
    if ops_resp.status_code != 200:
        print(json.dumps({"stage": "ops", "status_code": ops_resp.status_code, "body": ops_resp.text}, ensure_ascii=False))
        return 1

    output = {
        "task_id": task_id,
        "submit_status": submit_resp.json().get("status"),
        "task_status": status,
        "review": review_resp.json(),
        "result": results[0],
        "ops": ops_resp.json(),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
