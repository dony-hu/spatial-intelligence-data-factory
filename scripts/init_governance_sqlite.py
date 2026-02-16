import os
import sqlite3
from datetime import datetime

def init_db(db_path: str = "governance.db"):
    print(f"Initializing SQLite DB at {db_path}...")
    
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable Foreign Keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. addr_batch
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS addr_batch (
        batch_id VARCHAR(64) PRIMARY KEY,
        batch_name VARCHAR(255) NOT NULL,
        source VARCHAR(128),
        status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. addr_raw
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS addr_raw (
        raw_id VARCHAR(64) PRIMARY KEY,
        batch_id VARCHAR(64) NOT NULL REFERENCES addr_batch(batch_id),
        raw_text TEXT NOT NULL,
        province VARCHAR(64),
        city VARCHAR(64),
        district VARCHAR(64),
        street VARCHAR(128),
        detail TEXT,
        raw_hash VARCHAR(128) NOT NULL,
        ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. addr_canonical
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS addr_canonical (
        canonical_id VARCHAR(64) PRIMARY KEY,
        raw_id VARCHAR(64) NOT NULL REFERENCES addr_raw(raw_id),
        canon_text TEXT NOT NULL,
        province VARCHAR(64),
        city VARCHAR(64),
        district VARCHAR(64),
        street VARCHAR(128),
        road VARCHAR(128),
        house_no VARCHAR(64),
        building VARCHAR(64),
        unit_no VARCHAR(64),
        room_no VARCHAR(64),
        confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
        strategy VARCHAR(64) NOT NULL,
        evidence TEXT NOT NULL DEFAULT '{}',
        ruleset_version VARCHAR(64),
        trace_id VARCHAR(64),
        agent_run_id VARCHAR(64),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. addr_review
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS addr_review (
        review_id VARCHAR(64) PRIMARY KEY,
        raw_id VARCHAR(64) NOT NULL REFERENCES addr_raw(raw_id),
        review_status VARCHAR(32) NOT NULL,
        final_canon_text TEXT,
        reviewer VARCHAR(128),
        comment TEXT,
        reviewed_at TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. addr_ruleset
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS addr_ruleset (
        ruleset_id VARCHAR(64) PRIMARY KEY,
        version VARCHAR(64) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT 0,
        config_json TEXT NOT NULL,
        created_by VARCHAR(128),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. addr_change_request
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS addr_change_request (
        change_id VARCHAR(64) PRIMARY KEY,
        from_ruleset_id VARCHAR(64) NOT NULL REFERENCES addr_ruleset(ruleset_id),
        to_ruleset_id VARCHAR(64) NOT NULL REFERENCES addr_ruleset(ruleset_id),
        baseline_task_id VARCHAR(64) NOT NULL,
        candidate_task_id VARCHAR(64) NOT NULL,
        diff_json TEXT NOT NULL DEFAULT '{}',
        scorecard_json TEXT NOT NULL DEFAULT '{}',
        recommendation VARCHAR(32) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'pending',
        approved_by VARCHAR(128),
        approved_at TIMESTAMP,
        review_comment TEXT,
        evidence_bullets TEXT NOT NULL DEFAULT '[]',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 7. addr_task_run
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS addr_task_run (
        task_id VARCHAR(64) PRIMARY KEY,
        batch_id VARCHAR(64),
        status VARCHAR(32) NOT NULL,
        retry_count INT NOT NULL DEFAULT 0,
        error_code VARCHAR(64),
        error_message TEXT,
        trace_id VARCHAR(64),
        agent_run_id VARCHAR(64),
        runtime VARCHAR(32),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMP
    );
    """)

    # 8. addr_audit_event
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS addr_audit_event (
        event_id VARCHAR(64) PRIMARY KEY,
        event_type VARCHAR(64) NOT NULL,
        caller VARCHAR(128) NOT NULL,
        payload TEXT NOT NULL DEFAULT '{}',
        related_change_id VARCHAR(64),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 9. api_audit_log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_audit_log (
        audit_id VARCHAR(64) PRIMARY KEY,
        route VARCHAR(255) NOT NULL,
        method VARCHAR(16) NOT NULL,
        status_code INT,
        trace_id VARCHAR(64),
        task_id VARCHAR(64),
        actor VARCHAR(128),
        message TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 10. agent_execution_log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_execution_log (
        execution_id VARCHAR(64) PRIMARY KEY,
        task_id VARCHAR(64) NOT NULL,
        runtime VARCHAR(32) NOT NULL,
        latency_ms INT,
        success BOOLEAN NOT NULL,
        error_type VARCHAR(64),
        trace_id VARCHAR(64),
        agent_run_id VARCHAR(64),
        payload_json TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print("SQLite DB initialized successfully.")

if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL", "sqlite:///governance.db")
    if db_url.startswith("sqlite:///"):
        path = db_url.replace("sqlite:///", "")
        init_db(path)
    else:
        print("DATABASE_URL is not sqlite, skipping init.")
