    CREATE SCHEMA IF NOT EXISTS trust_meta;

CREATE TABLE IF NOT EXISTS trust_meta.source_registry (
    namespace_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    trust_level TEXT NOT NULL,
    license TEXT NOT NULL,
    entrypoint TEXT NOT NULL,
    update_frequency TEXT NOT NULL,
    fetch_method TEXT NOT NULL,
    parser_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    validator_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    allowed_use_notes TEXT NOT NULL,
    access_mode TEXT NOT NULL,
    robots_tos_flags JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (namespace_id, source_id)
);

CREATE TABLE IF NOT EXISTS trust_meta.source_schedule (
    namespace_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    schedule_type TEXT NOT NULL,
    schedule_spec TEXT NOT NULL,
    window_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (namespace_id, source_id),
    FOREIGN KEY (namespace_id, source_id) REFERENCES trust_meta.source_registry(namespace_id, source_id)
);

CREATE TABLE IF NOT EXISTS trust_meta.source_snapshot (
    namespace_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    version_tag TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    etag TEXT,
    last_modified TEXT,
    content_hash TEXT NOT NULL,
    raw_uri TEXT NOT NULL,
    parsed_uri TEXT NOT NULL,
    parsed_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL,
    row_count BIGINT NOT NULL DEFAULT 0,
    FOREIGN KEY (namespace_id, source_id) REFERENCES trust_meta.source_registry(namespace_id, source_id),
    PRIMARY KEY (namespace_id, snapshot_id)
);

CREATE TABLE IF NOT EXISTS trust_meta.snapshot_quality_report (
    namespace_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    report_json JSONB NOT NULL,
    quality_score INTEGER NOT NULL,
    validator_version TEXT NOT NULL,
    PRIMARY KEY (namespace_id, snapshot_id),
    FOREIGN KEY (namespace_id, snapshot_id) REFERENCES trust_meta.source_snapshot(namespace_id, snapshot_id)
);

CREATE TABLE IF NOT EXISTS trust_meta.snapshot_diff_report (
    namespace_id TEXT NOT NULL,
    base_snapshot_id TEXT NOT NULL,
    new_snapshot_id TEXT NOT NULL,
    diff_json JSONB NOT NULL,
    diff_severity TEXT NOT NULL,
    PRIMARY KEY (namespace_id, new_snapshot_id),
    FOREIGN KEY (namespace_id, base_snapshot_id) REFERENCES trust_meta.source_snapshot(namespace_id, snapshot_id),
    FOREIGN KEY (namespace_id, new_snapshot_id) REFERENCES trust_meta.source_snapshot(namespace_id, snapshot_id)
);

CREATE TABLE IF NOT EXISTS trust_meta.active_release (
    namespace_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    active_snapshot_id TEXT NOT NULL,
    activated_by TEXT NOT NULL,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activation_note TEXT,
    PRIMARY KEY (namespace_id, source_id),
    FOREIGN KEY (namespace_id, source_id) REFERENCES trust_meta.source_registry(namespace_id, source_id),
    FOREIGN KEY (namespace_id, active_snapshot_id) REFERENCES trust_meta.source_snapshot(namespace_id, snapshot_id)
);

CREATE TABLE IF NOT EXISTS trust_meta.audit_event (
    namespace_id TEXT NOT NULL,
    event_id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    event_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trust_meta.validation_replay_run (
    namespace_id TEXT NOT NULL,
    replay_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL,
    request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    replay_result JSONB NOT NULL DEFAULT '{}'::jsonb,
    schema_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (namespace_id, snapshot_id) REFERENCES trust_meta.source_snapshot(namespace_id, snapshot_id)
);

CREATE INDEX IF NOT EXISTS idx_validation_replay_ns_created
    ON trust_meta.validation_replay_run(namespace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_validation_replay_ns_snapshot
    ON trust_meta.validation_replay_run(namespace_id, snapshot_id);

CREATE SCHEMA IF NOT EXISTS trust_db;

CREATE TABLE IF NOT EXISTS trust_db.admin_division (
    namespace_id TEXT NOT NULL,
    adcode TEXT NOT NULL,
    name TEXT NOT NULL,
    level TEXT NOT NULL,
    parent_adcode TEXT,
    name_aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    source_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    PRIMARY KEY (namespace_id, adcode, source_id, snapshot_id)
);

CREATE TABLE IF NOT EXISTS trust_db.place_name_index (
    namespace_id TEXT NOT NULL,
    place_id TEXT NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    type TEXT NOT NULL,
    admin_adcode TEXT,
    centroid TEXT,
    confidence_hint DOUBLE PRECISION,
    source_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    PRIMARY KEY (namespace_id, place_id, source_id, snapshot_id)
);

CREATE TABLE IF NOT EXISTS trust_db.road_index (
    namespace_id TEXT NOT NULL,
    road_id TEXT NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    admin_adcode TEXT,
    geometry_ref TEXT,
    source_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    PRIMARY KEY (namespace_id, road_id, source_id, snapshot_id)
);

CREATE TABLE IF NOT EXISTS trust_db.poi_index (
    namespace_id TEXT NOT NULL,
    poi_id TEXT NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    category TEXT,
    admin_adcode TEXT,
    centroid TEXT,
    source_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    PRIMARY KEY (namespace_id, poi_id, source_id, snapshot_id)
);

CREATE INDEX IF NOT EXISTS idx_admin_division_ns_name ON trust_db.admin_division(namespace_id, name);
CREATE INDEX IF NOT EXISTS idx_road_index_ns_name ON trust_db.road_index(namespace_id, normalized_name);
CREATE INDEX IF NOT EXISTS idx_poi_index_ns_name ON trust_db.poi_index(namespace_id, normalized_name);
