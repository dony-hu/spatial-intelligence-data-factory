"""Agent runtime persistence for single-node deployment."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now().isoformat()


class AgentRuntimeStore:
    """SQLite + local filesystem runtime store."""

    def __init__(self, db_path: str = "database/agent_runtime.db", base_dir: str = "runtime_store"):
        self.db_path = db_path
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()
        self.seed_default_processes()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS process_definition (
                    id TEXT PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    owner_agent TEXT NOT NULL,
                    current_version_id TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS process_version (
                    id TEXT PRIMARY KEY,
                    process_definition_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    goal TEXT,
                    input_contract_json TEXT,
                    output_contract_json TEXT,
                    quality_policy_json TEXT,
                    iteration_policy_json TEXT,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(process_definition_id, version),
                    FOREIGN KEY(process_definition_id) REFERENCES process_definition(id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS process_step (
                    id TEXT PRIMARY KEY,
                    process_version_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    step_code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    process_type TEXT NOT NULL,
                    input_contract_json TEXT,
                    output_contract_json TEXT,
                    gate_contract_json TEXT,
                    FOREIGN KEY(process_version_id) REFERENCES process_version(id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS process_gate (
                    id TEXT PRIMARY KEY,
                    process_version_id TEXT NOT NULL,
                    gate_code TEXT NOT NULL,
                    gate_level TEXT NOT NULL,
                    required INTEGER NOT NULL DEFAULT 1,
                    rule_json TEXT,
                    FOREIGN KEY(process_version_id) REFERENCES process_version(id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_run (
                    task_run_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    process_definition_id TEXT NOT NULL,
                    process_version_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_round INTEGER NOT NULL DEFAULT 0,
                    max_rounds INTEGER NOT NULL DEFAULT 1,
                    input_snapshot_ref TEXT,
                    output_snapshot_ref TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    ended_at TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_input (
                    input_id TEXT PRIMARY KEY,
                    task_run_id TEXT NOT NULL,
                    input_type TEXT NOT NULL,
                    source_uri TEXT,
                    storage_uri TEXT NOT NULL,
                    mime_type TEXT,
                    sha256 TEXT,
                    size_bytes INTEGER,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(task_run_id) REFERENCES task_run(task_run_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_step_run (
                    step_run_id TEXT PRIMARY KEY,
                    task_run_id TEXT NOT NULL,
                    step_code TEXT NOT NULL,
                    round INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    input_refs_json TEXT,
                    output_refs_json TEXT,
                    error_code TEXT,
                    error_detail TEXT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    FOREIGN KEY(task_run_id) REFERENCES task_run(task_run_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_output_json (
                    output_id TEXT PRIMARY KEY,
                    task_run_id TEXT NOT NULL,
                    output_type TEXT NOT NULL,
                    schema_version TEXT,
                    content_json TEXT NOT NULL,
                    content_sha256 TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(task_run_id) REFERENCES task_run(task_run_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS process_iteration_event (
                    id TEXT PRIMARY KEY,
                    process_definition_id TEXT NOT NULL,
                    from_version_id TEXT,
                    to_version_id TEXT,
                    trigger_type TEXT NOT NULL,
                    strategy_patch_json TEXT,
                    reason TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS process_draft (
                    draft_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    base_process_definition_id TEXT,
                    process_code TEXT,
                    process_name TEXT,
                    domain TEXT,
                    requirement TEXT,
                    goal TEXT,
                    plan_json TEXT,
                    process_doc_markdown TEXT,
                    llm_answer TEXT,
                    status TEXT NOT NULL DEFAULT 'editable',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS process_chat_turn (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    draft_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_task_run_task_id ON task_run(task_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_task_input_task_run_id ON task_input(task_run_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_task_step_task_run_id ON task_step_run(task_run_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_task_output_task_run_id ON task_output_json(task_run_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_process_draft_session_id ON process_draft(session_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_process_chat_turn_session_id ON process_chat_turn(session_id)")

            # Phase 1: Confirmation mechanism
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS confirmation_record (
                    confirmation_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    draft_id TEXT,
                    pending_operation_id TEXT,
                    operation_type TEXT NOT NULL,
                    operation_params_json TEXT,
                    confirmation_status TEXT NOT NULL,
                    confirmer_user_id TEXT,
                    confirmation_timestamp TEXT,
                    created_at TEXT NOT NULL,
                    confirmed_at TEXT,
                    expires_at TEXT
                )
                """
            )

            # Phase 1: Dialogue parsing schema validation
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_registry (
                    schema_id TEXT PRIMARY KEY,
                    intent_name TEXT NOT NULL UNIQUE,
                    json_schema TEXT NOT NULL,
                    required_params TEXT,
                    allowed_values_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS parsing_event (
                    parsing_event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    raw_llm_response TEXT,
                    parsed_json TEXT,
                    validation_status TEXT,
                    validation_errors_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            # Phase 2: Execution trace visualization
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS step_run_detail (
                    detail_id TEXT PRIMARY KEY,
                    step_run_id TEXT NOT NULL,
                    task_run_id TEXT NOT NULL,
                    step_code TEXT NOT NULL,
                    step_index INTEGER,
                    round_number INTEGER,
                    started_at TEXT,
                    ended_at TEXT,
                    duration_ms INTEGER,
                    status TEXT,
                    error_code TEXT,
                    error_detail TEXT,
                    input_count INTEGER,
                    output_count INTEGER,
                    summary_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(step_run_id) REFERENCES task_step_run(step_run_id),
                    FOREIGN KEY(task_run_id) REFERENCES task_run(task_run_id)
                )
                """
            )

            # Phase 2: Draft version history and comparison
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS draft_version_history (
                    history_id TEXT PRIMARY KEY,
                    draft_id TEXT NOT NULL,
                    version_sequence INTEGER,
                    process_code TEXT,
                    process_name TEXT,
                    domain TEXT,
                    goal TEXT,
                    plan_json TEXT,
                    process_doc_markdown TEXT,
                    changed_fields_json TEXT,
                    change_summary TEXT,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(draft_id) REFERENCES process_draft(draft_id)
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS draft_comparison (
                    comparison_id TEXT PRIMARY KEY,
                    draft_id TEXT,
                    version_a INTEGER,
                    version_b INTEGER,
                    diff_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            # Phase 3: External API integration
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS external_api_cache (
                    cache_key TEXT PRIMARY KEY,
                    api_name TEXT NOT NULL,
                    request_hash TEXT,
                    response_json TEXT,
                    status_code INTEGER,
                    cached_at TEXT NOT NULL,
                    expires_at TEXT,
                    hit_count INTEGER DEFAULT 0
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS api_call_log (
                    call_id TEXT PRIMARY KEY,
                    api_name TEXT NOT NULL,
                    request_json TEXT,
                    response_json TEXT,
                    status_code INTEGER,
                    error_type TEXT,
                    error_detail TEXT,
                    latency_ms INTEGER,
                    created_at TEXT NOT NULL,
                    task_run_id TEXT,
                    FOREIGN KEY(task_run_id) REFERENCES task_run(task_run_id)
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS api_capability_registry (
                    capability_id TEXT PRIMARY KEY,
                    api_name TEXT NOT NULL UNIQUE,
                    provider TEXT,
                    status TEXT NOT NULL,
                    config_json TEXT,
                    fallback_to TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            # Create indices for new tables
            cur.execute("CREATE INDEX IF NOT EXISTS idx_confirmation_session_id ON confirmation_record(session_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_parsing_event_session_id ON parsing_event(session_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_draft_version_history_draft_id ON draft_version_history(draft_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_external_api_cache_api_name ON external_api_cache(api_name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_api_call_log_api_name ON api_call_log(api_name)")

    def seed_default_processes(self) -> None:
        """Seed default process definitions if absent."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS cnt FROM process_definition")
            if int(cur.fetchone()["cnt"]) > 0:
                return

        self._create_process_with_release(
            code="ADDR_GOVERNANCE",
            name="地址治理工艺",
            domain="address_governance",
            goal="完成地址解析、标准化与质量校验。",
            steps=[
                ("PARSING", "地址解析", "address_parser_tool", "自动化"),
                ("STANDARDIZATION", "地址标准化", "address_standardizer_tool", "自动化"),
                ("TIEYUAN_VALIDATE", "贴源字段校验", "tieyuan_validation_tool", "自动化"),
            ],
        )
        self._create_process_with_release(
            code="ADDR_TO_GRAPH",
            name="地址到图谱工艺",
            domain="address_to_graph",
            goal="完成实体抽取、关系构建与图谱门禁。",
            steps=[
                ("EXTRACTION", "实体抽取", "graph_extraction_tool", "自动化"),
                ("REL_BUILD", "关系构建", "graph_relationship_tool", "自动化"),
                ("GRAPH_GATE", "图谱门禁", "graph_gate_tool", "自动化"),
            ],
        )
        self._create_process_with_release(
            code="ADDR_GOV_AND_GRAPH_COMBINED",
            name="地址治理与图谱合并工艺",
            domain="address_governance",
            goal="一次任务完成地址治理与图谱生产。",
            steps=[
                ("PARSING", "地址解析", "address_parser_tool", "自动化"),
                ("STANDARDIZATION", "地址标准化", "address_standardizer_tool", "自动化"),
                ("TIEYUAN_VALIDATE", "贴源字段校验", "tieyuan_validation_tool", "自动化"),
                ("EXTRACTION", "实体抽取", "graph_extraction_tool", "自动化"),
                ("REL_BUILD", "关系构建", "graph_relationship_tool", "自动化"),
                ("GRAPH_GATE", "图谱门禁", "graph_gate_tool", "自动化"),
            ],
        )

    def _create_process_with_release(
        self,
        code: str,
        name: str,
        domain: str,
        goal: str,
        steps: List[tuple],
    ) -> None:
        now = _now_iso()
        process_id = f"procdef_{uuid.uuid4().hex[:12]}"
        version_id = f"procver_{uuid.uuid4().hex[:12]}"
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO process_definition
                (id, code, name, domain, owner_agent, current_version_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (process_id, code, name, domain, "process_expert", version_id, now, now),
            )
            cur.execute(
                """
                INSERT INTO process_version
                (id, process_definition_id, version, status, goal, input_contract_json, output_contract_json,
                 quality_policy_json, iteration_policy_json, created_by, created_at)
                VALUES (?, ?, '1.0.0', 'released', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    process_id,
                    goal,
                    json.dumps({"type": "object", "required": ["inputs"]}, ensure_ascii=False),
                    json.dumps({"type": "object", "required": ["records"]}, ensure_ascii=False),
                    json.dumps({"quality_threshold": 0.9}, ensure_ascii=False),
                    json.dumps({"max_rounds": 3, "stop_on_no_gain": True}, ensure_ascii=False),
                    "process_expert",
                    now,
                ),
            )
            for idx, (step_code, step_name, tool_name, process_type) in enumerate(steps, start=1):
                cur.execute(
                    """
                    INSERT INTO process_step
                    (id, process_version_id, seq, step_code, name, tool_name, process_type,
                     input_contract_json, output_contract_json, gate_contract_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"pstep_{uuid.uuid4().hex[:12]}",
                        version_id,
                        idx,
                        step_code,
                        step_name,
                        tool_name,
                        process_type,
                        json.dumps({"schema": "default_input"}, ensure_ascii=False),
                        json.dumps({"schema": "default_output"}, ensure_ascii=False),
                        json.dumps({"required": True}, ensure_ascii=False),
                    ),
                )
            # process_expert聚焦工艺设计与执行门禁，不引入发布窗口类门禁。
            for gate_code, gate_level, required in [
                ("kpi_frozen", "design", 1),
                ("compliance_approved", "runtime", 1),
            ]:
                cur.execute(
                    """
                    INSERT INTO process_gate
                    (id, process_version_id, gate_code, gate_level, required, rule_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"pgate_{uuid.uuid4().hex[:12]}",
                        version_id,
                        gate_code,
                        gate_level,
                        required,
                        json.dumps({"description": gate_code}, ensure_ascii=False),
                    ),
                )

    def get_released_process(self, process_code: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT pd.id AS process_definition_id, pd.code, pd.name, pd.domain,
                       pv.id AS process_version_id, pv.version, pv.goal, pv.status
                FROM process_definition pd
                JOIN process_version pv ON pv.id = pd.current_version_id
                WHERE pd.code = ? AND pd.status = 'active' AND pv.status = 'released'
                """,
                (process_code,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def list_process_definitions(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, code, name, domain, owner_agent, current_version_id, status, created_at, updated_at
                FROM process_definition
                ORDER BY created_at DESC
                """
            )
            return [dict(r) for r in cur.fetchall()]

    def create_process_definition(self, code: str, name: str, domain: str, owner_agent: str) -> Dict[str, Any]:
        process_id = f"procdef_{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO process_definition
                (id, code, name, domain, owner_agent, current_version_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, NULL, 'active', ?, ?)
                """,
                (process_id, code, name, domain, owner_agent, now, now),
            )
            cur.execute("SELECT * FROM process_definition WHERE id = ?", (process_id,))
            return dict(cur.fetchone())

    def create_process_version(
        self,
        process_definition_id: str,
        version: str,
        goal: str,
        steps: List[Dict[str, Any]],
        publish: bool = False,
        created_by: str = "process_expert",
    ) -> Dict[str, Any]:
        version_id = f"procver_{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        status = "released" if publish else "draft"
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO process_version
                (id, process_definition_id, version, status, goal, input_contract_json, output_contract_json,
                 quality_policy_json, iteration_policy_json, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    process_definition_id,
                    version,
                    status,
                    goal,
                    json.dumps({"type": "object", "required": ["inputs"]}, ensure_ascii=False),
                    json.dumps({"type": "object", "required": ["records"]}, ensure_ascii=False),
                    json.dumps({"quality_threshold": 0.9}, ensure_ascii=False),
                    json.dumps({"max_rounds": 3}, ensure_ascii=False),
                    created_by,
                    now,
                ),
            )
            for idx, item in enumerate(steps or [], start=1):
                cur.execute(
                    """
                    INSERT INTO process_step
                    (id, process_version_id, seq, step_code, name, tool_name, process_type,
                     input_contract_json, output_contract_json, gate_contract_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"pstep_{uuid.uuid4().hex[:12]}",
                        version_id,
                        idx,
                        str(item.get("step_code") or f"S{idx}"),
                        str(item.get("name") or f"步骤{idx}"),
                        str(item.get("tool_name") or "automation_tool"),
                        str(item.get("process_type") or "自动化"),
                        json.dumps(item.get("input_contract") or {"schema": "default_input"}, ensure_ascii=False),
                        json.dumps(item.get("output_contract") or {"schema": "default_output"}, ensure_ascii=False),
                        json.dumps(item.get("gate_contract") or {"required": True}, ensure_ascii=False),
                    ),
                )
            if publish:
                cur.execute(
                    "UPDATE process_definition SET current_version_id = ?, updated_at = ? WHERE id = ?",
                    (version_id, now, process_definition_id),
                )
            cur.execute("SELECT * FROM process_version WHERE id = ?", (version_id,))
            return dict(cur.fetchone())

    def list_process_versions(self, process_definition_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, process_definition_id, version, status, goal, created_by, created_at
                FROM process_version
                WHERE process_definition_id = ?
                ORDER BY created_at DESC
                """,
                (process_definition_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def list_tasks_by_process_definition(self, process_definition_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT task_run_id, task_id, process_definition_id, process_version_id, status, current_round, max_rounds, created_at, updated_at, ended_at
                FROM task_run
                WHERE process_definition_id = ?
                ORDER BY created_at DESC
                """,
                (process_definition_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def create_task_run(
        self,
        task_id: str,
        process_definition_id: str,
        process_version_id: str,
        max_rounds: int,
        input_snapshot_ref: Optional[str] = None,
    ) -> str:
        task_run_id = f"trun_{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO task_run
                (task_run_id, task_id, process_definition_id, process_version_id, status, current_round, max_rounds,
                 input_snapshot_ref, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'running', 0, ?, ?, ?, ?)
                """,
                (task_run_id, task_id, process_definition_id, process_version_id, int(max_rounds), input_snapshot_ref, now, now),
            )
        return task_run_id

    def update_task_run(
        self,
        task_run_id: str,
        status: str,
        current_round: Optional[int] = None,
        output_snapshot_ref: Optional[str] = None,
        ended: bool = False,
    ) -> None:
        now = _now_iso()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM task_run WHERE task_run_id = ?", (task_run_id,))
            row = cur.fetchone()
            if not row:
                return
            payload = dict(row)
            payload["status"] = status
            payload["updated_at"] = now
            if current_round is not None:
                payload["current_round"] = int(current_round)
            if output_snapshot_ref is not None:
                payload["output_snapshot_ref"] = output_snapshot_ref
            if ended:
                payload["ended_at"] = now
            cur.execute(
                """
                UPDATE task_run
                SET status = ?, current_round = ?, output_snapshot_ref = ?, updated_at = ?, ended_at = COALESCE(?, ended_at)
                WHERE task_run_id = ?
                """,
                (
                    payload["status"],
                    payload["current_round"],
                    payload.get("output_snapshot_ref"),
                    payload["updated_at"],
                    payload.get("ended_at"),
                    task_run_id,
                ),
            )

    def add_task_input(
        self,
        task_run_id: str,
        input_type: str,
        source_uri: str,
        mime_type: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        input_id = f"in_{uuid.uuid4().hex[:12]}"
        task_dir = self.base_dir / "tasks" / task_run_id / "input"
        task_dir.mkdir(parents=True, exist_ok=True)
        sha = hashlib.sha256(content).hexdigest()
        ext = self._ext_from_mime(mime_type)
        file_name = f"{input_id}{ext}"
        file_path = task_dir / file_name
        file_path.write_bytes(content)
        storage_uri = f"file://{file_path.resolve()}"
        now = _now_iso()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO task_input
                (input_id, task_run_id, input_type, source_uri, storage_uri, mime_type, sha256, size_bytes, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    input_id,
                    task_run_id,
                    input_type,
                    source_uri,
                    storage_uri,
                    mime_type,
                    sha,
                    len(content),
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now,
                ),
            )
        return input_id

    def add_step_run(
        self,
        task_run_id: str,
        step_code: str,
        round_index: int,
        status: str,
        input_refs: Optional[List[str]] = None,
        output_refs: Optional[List[str]] = None,
        error_code: Optional[str] = None,
        error_detail: Optional[str] = None,
    ) -> str:
        step_run_id = f"srun_{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO task_step_run
                (step_run_id, task_run_id, step_code, round, status, input_refs_json, output_refs_json, error_code, error_detail, started_at, ended_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step_run_id,
                    task_run_id,
                    step_code,
                    int(round_index),
                    status,
                    json.dumps(input_refs or [], ensure_ascii=False),
                    json.dumps(output_refs or [], ensure_ascii=False),
                    error_code,
                    error_detail,
                    now,
                    now,
                ),
            )
        return step_run_id

    def add_output_json(
        self,
        task_run_id: str,
        output_type: str,
        content: Dict[str, Any],
        schema_version: str = "v1",
    ) -> str:
        output_id = f"out_{uuid.uuid4().hex[:12]}"
        text = json.dumps(content, ensure_ascii=False)
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        now = _now_iso()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO task_output_json
                (output_id, task_run_id, output_type, schema_version, content_json, content_sha256, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (output_id, task_run_id, output_type, schema_version, text, sha, now),
            )
        return output_id

    def get_task_run(self, task_run_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM task_run WHERE task_run_id = ?", (task_run_id,))
            row = cur.fetchone()
            if not row:
                return None
            result = dict(row)
            cur.execute("SELECT * FROM task_input WHERE task_run_id = ? ORDER BY created_at", (task_run_id,))
            result["inputs"] = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT * FROM task_step_run WHERE task_run_id = ? ORDER BY started_at", (task_run_id,))
            result["steps"] = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT * FROM task_output_json WHERE task_run_id = ? ORDER BY created_at", (task_run_id,))
            result["outputs"] = [dict(r) for r in cur.fetchall()]
            return result

    def upsert_process_draft(
        self,
        draft_id: str,
        session_id: str,
        process_code: str,
        process_name: str,
        domain: str,
        requirement: str,
        goal: str,
        plan: Dict[str, Any],
        process_doc_markdown: str,
        llm_answer: str,
        base_process_definition_id: Optional[str] = None,
        status: str = "editable",
    ) -> Dict[str, Any]:
        now = _now_iso()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT draft_id, created_at FROM process_draft WHERE draft_id = ?", (draft_id,))
            row = cur.fetchone()
            created_at = str(row["created_at"]) if row else now
            if row:
                cur.execute(
                    """
                    UPDATE process_draft
                    SET session_id = ?, base_process_definition_id = ?, process_code = ?, process_name = ?, domain = ?,
                        requirement = ?, goal = ?, plan_json = ?, process_doc_markdown = ?, llm_answer = ?, status = ?, updated_at = ?
                    WHERE draft_id = ?
                    """,
                    (
                        session_id,
                        base_process_definition_id,
                        process_code,
                        process_name,
                        domain,
                        requirement,
                        goal,
                        json.dumps(plan or {}, ensure_ascii=False),
                        process_doc_markdown,
                        llm_answer,
                        status,
                        now,
                        draft_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO process_draft
                    (draft_id, session_id, base_process_definition_id, process_code, process_name, domain, requirement, goal,
                     plan_json, process_doc_markdown, llm_answer, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        draft_id,
                        session_id,
                        base_process_definition_id,
                        process_code,
                        process_name,
                        domain,
                        requirement,
                        goal,
                        json.dumps(plan or {}, ensure_ascii=False),
                        process_doc_markdown,
                        llm_answer,
                        status,
                        created_at,
                        now,
                    ),
                )
            cur.execute("SELECT * FROM process_draft WHERE draft_id = ?", (draft_id,))
            result = dict(cur.fetchone())
            result["plan"] = json.loads(result.get("plan_json") or "{}")
            return result

    def get_process_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM process_draft WHERE draft_id = ?", (draft_id,))
            row = cur.fetchone()
            if not row:
                return None
            result = dict(row)
            result["plan"] = json.loads(result.get("plan_json") or "{}")
            return result

    def get_latest_editable_draft_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM process_draft
                WHERE session_id = ? AND status = 'editable'
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            result = dict(row)
            result["plan"] = json.loads(result.get("plan_json") or "{}")
            return result

    def mark_process_draft_published(self, draft_id: str) -> None:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE process_draft SET status = 'published', updated_at = ? WHERE draft_id = ?",
                (_now_iso(), draft_id),
            )

    def append_process_chat_turn(self, session_id: str, role: str, content: str, draft_id: Optional[str] = None) -> str:
        turn_id = f"turn_{uuid.uuid4().hex[:12]}"
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO process_chat_turn
                (turn_id, session_id, draft_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (turn_id, session_id, draft_id, role, content, _now_iso()),
            )
        return turn_id

    @staticmethod
    def _ext_from_mime(mime_type: str) -> str:
        mapping = {
            "text/plain": ".txt",
            "application/json": ".json",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "application/pdf": ".pdf",
        }
        return mapping.get(mime_type, ".bin")

    # ===== Phase 1: Confirmation mechanism =====

    def create_confirmation_record(
        self,
        session_id: str,
        operation_type: str,
        operation_params: Dict[str, Any],
        draft_id: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> str:
        """Create a new confirmation record."""
        confirmation_id = f"confirm_{uuid.uuid4().hex[:12]}"
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO confirmation_record
                (confirmation_id, session_id, draft_id, operation_type, operation_params_json,
                 confirmation_status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    confirmation_id,
                    session_id,
                    draft_id,
                    operation_type,
                    json.dumps(operation_params, ensure_ascii=False),
                    "pending",
                    _now_iso(),
                    expires_at,
                ),
            )
        return confirmation_id

    def get_confirmation_record(self, confirmation_id: str) -> Optional[Dict[str, Any]]:
        """Get confirmation record by ID."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM confirmation_record WHERE confirmation_id = ?", (confirmation_id,))
            row = cur.fetchone()
            if not row:
                return None
            result = dict(row)
            result["operation_params"] = json.loads(result.get("operation_params_json") or "{}")
            return result

    def update_confirmation_status(
        self, confirmation_id: str, status: str, confirmer_user_id: Optional[str] = None
    ) -> None:
        """Update confirmation record status."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE confirmation_record
                SET confirmation_status = ?, confirmed_at = ?, confirmer_user_id = ?
                WHERE confirmation_id = ?
                """,
                (status, _now_iso() if status != "pending" else None, confirmer_user_id, confirmation_id),
            )

    # ===== Phase 1: Dialogue parsing schema validation =====

    def log_parsing_event(
        self,
        session_id: str,
        raw_llm_response: str,
        parsed_json: str,
        validation_status: str,
        validation_errors: Optional[str] = None,
    ) -> str:
        """Log a dialogue parsing event."""
        parsing_event_id = f"parse_{uuid.uuid4().hex[:12]}"
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO parsing_event
                (parsing_event_id, session_id, raw_llm_response, parsed_json,
                 validation_status, validation_errors_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parsing_event_id,
                    session_id,
                    raw_llm_response,
                    parsed_json,
                    validation_status,
                    validation_errors or "[]",
                    _now_iso(),
                ),
            )
        return parsing_event_id

    # ===== Phase 2: Draft version history =====

    def add_draft_version_history(
        self, draft_id: str, version_sequence: int, old_version: Dict[str, Any], change_summary: Optional[str] = None
    ) -> str:
        """Add a draft version to history."""
        history_id = f"hist_{uuid.uuid4().hex[:12]}"
        changed_fields = {}
        if version_sequence > 1:
            # Detect which fields changed
            for field in ["process_code", "process_name", "goal", "domain", "plan_json", "process_doc_markdown"]:
                changed_fields[field] = True

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO draft_version_history
                (history_id, draft_id, version_sequence, process_code, process_name, domain, goal,
                 plan_json, process_doc_markdown, changed_fields_json, change_summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    history_id,
                    draft_id,
                    version_sequence,
                    old_version.get("process_code"),
                    old_version.get("process_name"),
                    old_version.get("domain"),
                    old_version.get("goal"),
                    old_version.get("plan_json"),
                    old_version.get("process_doc_markdown"),
                    json.dumps(changed_fields, ensure_ascii=False),
                    change_summary or "修改草案",
                    _now_iso(),
                ),
            )
        return history_id

    def list_draft_version_history(self, draft_id: str) -> List[Dict[str, Any]]:
        """List all versions of a draft."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM draft_version_history
                WHERE draft_id = ?
                ORDER BY version_sequence ASC
                """,
                (draft_id,),
            )
            rows = cur.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                result["changed_fields"] = json.loads(result.get("changed_fields_json") or "{}")
                results.append(result)
            return results

    def get_draft_version(self, draft_id: str, version_sequence: int) -> Optional[Dict[str, Any]]:
        """Get a specific draft version."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM draft_version_history
                WHERE draft_id = ? AND version_sequence = ?
                """,
                (draft_id, version_sequence),
            )
            row = cur.fetchone()
            if not row:
                return None
            result = dict(row)
            result["changed_fields"] = json.loads(result.get("changed_fields_json") or "{}")
            return result

    # ===== Phase 3: External API integration helpers =====

    def log_api_call(
        self,
        api_name: str,
        request_json: str,
        response_json: str,
        error_type: Optional[str] = None,
        latency_ms: int = 0,
        task_run_id: Optional[str] = None,
    ) -> str:
        """Log an external API call."""
        call_id = f"api_{uuid.uuid4().hex[:12]}"
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO api_call_log
                (call_id, api_name, request_json, response_json, error_type, latency_ms, created_at, task_run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (call_id, api_name, request_json, response_json, error_type, latency_ms, _now_iso(), task_run_id),
            )
        return call_id

    def get_db(self):
        """Get a database connection context manager."""
        return self.get_connection()
