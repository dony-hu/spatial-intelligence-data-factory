"""工艺数据库操作 API 封装。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.agent_runtime_store import AgentRuntimeStore


def _default_process_steps() -> List[Dict[str, Any]]:
    return [
        {"step_code": "INPUT_PREP", "name": "输入准备", "tool_name": "input_prep_tool", "process_type": "自动化"},
        {"step_code": "PROCESS", "name": "工艺处理", "tool_name": "process_tool", "process_type": "自动化"},
        {"step_code": "OUTPUT_JSON", "name": "输出入库", "tool_name": "output_json_tool", "process_type": "自动化"},
    ]


class ProcessDBApi:
    """受控数据库操作集合，仅通过明确意图调用。"""

    def __init__(self, runtime_store: AgentRuntimeStore, process_design_drafts: Dict[str, Dict[str, Any]]):
        self.runtime_store = runtime_store
        self.process_design_drafts = process_design_drafts

    def find_process_definition(self, process_definition_id: str = "", code: str = "") -> Optional[Dict[str, Any]]:
        items = self.runtime_store.list_process_definitions()
        if process_definition_id:
            hit = next((x for x in items if str(x.get("id") or "") == process_definition_id), None)
            if hit:
                return hit
        if code:
            code_u = code.upper()
            hit = next((x for x in items if str(x.get("code") or "").upper() == code_u), None)
            if hit:
                return hit
        return None

    def create_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code = str(params.get("code") or "").strip().upper()
        if not code:
            return {"status": "error", "error": "缺少 code", "intent": "create_process"}
        name = str(params.get("name") or f"{code} 工艺").strip()
        domain = str(params.get("domain") or "address_governance").strip()
        item = self.runtime_store.create_process_definition(code=code, name=name, domain=domain, owner_agent="process_expert")
        return {"status": "ok", "intent": "create_process", "process_definition": item}

    def query_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code = str(params.get("code") or "").strip().upper()
        name = str(params.get("name") or "").strip()
        items = self.runtime_store.list_process_definitions()
        if code:
            items = [x for x in items if str(x.get("code") or "").upper() == code]
        if name:
            items = [x for x in items if name in str(x.get("name") or "")]
        return {"status": "ok", "intent": "query_process", "items": items}

    def query_version(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code = str(params.get("code") or "").strip().upper()
        process_definition_id = str(params.get("process_definition_id") or "").strip()
        if not process_definition_id and code:
            hit = self.find_process_definition(code=code)
            process_definition_id = str((hit or {}).get("id") or "")
        if not process_definition_id:
            return {"status": "ok", "intent": "query_version", "items": []}
        return {
            "status": "ok",
            "intent": "query_version",
            "process_definition_id": process_definition_id,
            "items": self.runtime_store.list_process_versions(process_definition_id),
        }

    def create_version(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code = str(params.get("code") or "").strip().upper()
        process_definition_id = str(params.get("process_definition_id") or "").strip()
        if not process_definition_id and code:
            hit = self.find_process_definition(code=code)
            process_definition_id = str((hit or {}).get("id") or "")
        version = str(params.get("version") or "").strip()
        if not process_definition_id or not version:
            return {"status": "error", "error": "缺少 process_definition_id/code 或 version", "intent": "create_version"}
        goal = str(params.get("goal") or "对话式创建版本").strip()
        publish = bool(params.get("publish", True))
        item = self.runtime_store.create_process_version(
            process_definition_id=process_definition_id,
            version=version,
            goal=goal,
            steps=params.get("steps") or _default_process_steps(),
            publish=publish,
            created_by="process_expert",
        )
        return {"status": "ok", "intent": "create_version", "process_version": item}

    def publish_draft(self, params: Dict[str, Any]) -> Dict[str, Any]:
        draft_id = str(params.get("draft_id") or "").strip()
        if not draft_id:
            return {"status": "error", "error": "缺少 draft_id", "intent": "publish_draft"}
        draft = self.process_design_drafts.get(draft_id)
        if not draft:
            return {"status": "error", "error": "draft_id 不存在", "intent": "publish_draft"}
        existing = self.find_process_definition(code=str(draft.get("process_code") or ""))
        if existing:
            process_definition_id = existing["id"]
        else:
            created = self.runtime_store.create_process_definition(
                code=draft["process_code"],
                name=draft["process_name"],
                domain=draft["domain"],
                owner_agent="process_expert",
            )
            process_definition_id = created["id"]
        versions = self.runtime_store.list_process_versions(process_definition_id)
        next_minor = len(versions) + 1
        version = f"1.0.{next_minor}"
        ver = self.runtime_store.create_process_version(
            process_definition_id=process_definition_id,
            version=version,
            goal=draft.get("goal") or draft.get("requirement") or "",
            steps=_default_process_steps(),
            publish=True,
            created_by="process_expert",
        )
        return {
            "status": "ok",
            "intent": "publish_draft",
            "draft_id": draft_id,
            "process_definition_id": process_definition_id,
            "process_version_id": ver["id"],
            "version": ver["version"],
        }

    def query_process_tasks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code = str(params.get("code") or "").strip().upper()
        process_definition_id = str(params.get("process_definition_id") or "").strip()
        if not process_definition_id and code:
            hit = self.find_process_definition(code=code)
            process_definition_id = str((hit or {}).get("id") or "")
        if not process_definition_id:
            return {"status": "error", "error": "缺少 process_definition_id/code", "intent": "query_process_tasks"}
        return {
            "status": "ok",
            "intent": "query_process_tasks",
            "items": self.runtime_store.list_tasks_by_process_definition(process_definition_id),
        }

    def query_task_io(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_run_id = str(params.get("task_run_id") or "").strip()
        if not task_run_id:
            return {"status": "error", "error": "缺少 task_run_id", "intent": "query_task_io"}
        item = self.runtime_store.get_task_run(task_run_id)
        if not item:
            return {"status": "error", "error": "task_run_id 不存在", "intent": "query_task_io"}
        return {"status": "ok", "intent": "query_task_io", "task_run": item}

    def execute(self, intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
        handlers = {
            "create_process": self.create_process,
            "query_process": self.query_process,
            "query_version": self.query_version,
            "create_version": self.create_version,
            "publish_draft": self.publish_draft,
            "query_process_tasks": self.query_process_tasks,
            "query_task_io": self.query_task_io,
        }
        fn = handlers.get(intent)
        if not fn:
            return {"status": "ok", "intent": "chat", "message": "该轮对话未触发数据库操作"}
        return fn(params)
