CREATE INDEX IF NOT EXISTS idx_addr_raw_hash ON addr_raw(raw_hash);
CREATE INDEX IF NOT EXISTS idx_addr_raw_text_trgm ON addr_raw USING gin(raw_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_addr_canonical_text_trgm ON addr_canonical USING gin(canon_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_addr_task_run_status ON addr_task_run(task_id, status);
CREATE INDEX IF NOT EXISTS idx_addr_change_request_status ON addr_change_request(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_addr_change_request_to_ruleset ON addr_change_request(to_ruleset_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_addr_audit_event_change ON addr_audit_event(related_change_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_addr_workpackage_publish_key ON addr_workpackage_publish(workpackage_id, version);
CREATE INDEX IF NOT EXISTS idx_addr_observation_event_trace ON addr_observation_event(trace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_addr_observation_event_type ON addr_observation_event(source_service, event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_addr_observation_metric_name_window ON addr_observation_metric(metric_name, window_end DESC);
CREATE INDEX IF NOT EXISTS idx_addr_alert_event_status_created ON addr_alert_event(status, created_at DESC);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_addr_review_status'
    ) THEN
        ALTER TABLE addr_review
            ADD CONSTRAINT chk_addr_review_status
            CHECK (review_status IN ('approved', 'rejected', 'edited'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_addr_change_request_status'
    ) THEN
        ALTER TABLE addr_change_request
            ADD CONSTRAINT chk_addr_change_request_status
            CHECK (status IN ('pending', 'approved', 'rejected'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_addr_task_retry_count'
    ) THEN
        ALTER TABLE addr_task_run
            ADD CONSTRAINT chk_addr_task_retry_count
            CHECK (retry_count >= 0);
    END IF;
END $$;
