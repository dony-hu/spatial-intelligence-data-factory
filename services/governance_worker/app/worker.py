from __future__ import annotations

import os


def main() -> None:
    queue_name = os.getenv("RQ_QUEUE", "governance")
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    print(f"governance worker bootstrap queue={queue_name} redis={redis_url}")
    print("Use rq worker runtime in deployment environment.")


if __name__ == "__main__":
    main()
