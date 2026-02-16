
import os
import json
import uuid
from services.governance_worker.app.jobs.governance_job import run as run_governance_job
from services.governance_api.app.repositories.governance_repository import REPOSITORY

# Mock payload
task_id = f"task_{uuid.uuid4().hex[:8]}"
mock_payload = {
    "task_id": task_id,
    "batch_name": "debug_batch_001",
    "ruleset_id": "default",
    "records": [
        {
            "raw_id": f"raw_{uuid.uuid4().hex[:8]}",
            "raw_text": "上海市浦东新区张江镇祖冲之路123号",
            "province": "上海市",
            "city": "上海市",
            "district": "浦东新区"
        }
    ]
}

print(f"Starting debug run for task_id: {task_id}")

# Ensure DB connection
os.environ["DATABASE_URL"] = "postgresql+psycopg://huda@localhost:5432/spatial_intelligence"
# Set LLM to non-strict to avoid blocking on missing API keys if any (will fallback)
os.environ["OPENHANDS_STRICT"] = "0"
# We might need an API KEY if we want real LLM call, otherwise it will fallback.
# For pipeline testing, fallback is fine as long as it writes to DB.
# If you have a key, uncomment below:
# os.environ["LLM_API_KEY"] = "your_key" 

try:
    # 1. Create task in DB first (usually API does this)
    REPOSITORY.create_task(
        task_id=task_id,
        batch_name=mock_payload["batch_name"],
        ruleset_id=mock_payload["ruleset_id"],
        status="PENDING",
        queue_backend="sync_debug",
        queue_message=""
    )
    print("Task created in DB.")

    # 2. Run the job
    result = run_governance_job(mock_payload)
    print(f"Job finished with result: {result}")

    # 3. Verify results in DB
    db_results = REPOSITORY.get_results(task_id)
    print(f"Found {len(db_results)} results in DB.")
    if len(db_results) > 0:
        print("Sample result:", json.dumps(db_results[0], ensure_ascii=False, indent=2))
        print("\n✅ Pipeline SUCCESS: Data flowed from input -> processing -> database.")
    else:
        print("\n❌ Pipeline FAILURE: No results found in database.")

except Exception as e:
    print(f"\n❌ Pipeline FAILURE with error: {e}")
    import traceback
    traceback.print_exc()
