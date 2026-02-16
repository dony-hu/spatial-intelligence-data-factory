from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


def _post(url: str) -> None:
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


def main() -> None:
    api_base = os.getenv("TRUST_API_BASE", "http://trust-api:8082")
    namespace = os.getenv("TRUST_NAMESPACE", "system.trust")
    source_ids = [s.strip() for s in os.getenv("TRUST_SCHEDULER_SOURCE_IDS", "").split(",") if s.strip()]
    interval = int(os.getenv("TRUST_SCHEDULER_INTERVAL_SECONDS", "3600"))

    while True:
        now = datetime.now(timezone.utc).isoformat()
        print(f"[trust-scheduler] tick at {now}, source_count={len(source_ids)}", flush=True)
        for source_id in source_ids:
            try:
                _post(f"{api_base}/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now")
                print(
                    json.dumps({"namespace": namespace, "source_id": source_id, "action": "fetch-now", "status": "ok"}),
                    flush=True,
                )
            except urllib.error.HTTPError as exc:
                print(
                    json.dumps(
                        {
                            "namespace": namespace,
                            "source_id": source_id,
                            "action": "fetch-now",
                            "status": "http_error",
                            "code": exc.code,
                        }
                    ),
                    flush=True,
                )
            except Exception as exc:  # pragma: no cover
                print(
                    json.dumps(
                        {
                            "namespace": namespace,
                            "source_id": source_id,
                            "action": "fetch-now",
                            "status": "error",
                            "error": str(exc),
                        }
                    ),
                    flush=True,
                )
        time.sleep(interval)


if __name__ == "__main__":
    main()
