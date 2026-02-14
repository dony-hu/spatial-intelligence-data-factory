CREATE INDEX IF NOT EXISTS idx_addr_raw_hash ON addr_raw(raw_hash);
CREATE INDEX IF NOT EXISTS idx_addr_raw_text_trgm ON addr_raw USING gin(raw_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_addr_canonical_text_trgm ON addr_canonical USING gin(canon_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_addr_task_run_status ON addr_task_run(task_id, status);

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
        WHERE conname = 'chk_addr_task_retry_count'
    ) THEN
        ALTER TABLE addr_task_run
            ADD CONSTRAINT chk_addr_task_retry_count
            CHECK (retry_count >= 0);
    END IF;
END $$;
