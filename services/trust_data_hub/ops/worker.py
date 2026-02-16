from __future__ import annotations

import os
import time
from datetime import datetime, timezone


def main() -> None:
    interval = int(os.getenv("TRUST_WORKER_POLL_SECONDS", "15"))
    while True:
        now = datetime.now(timezone.utc).isoformat()
        print(f"[trust-worker] heartbeat at {now}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
