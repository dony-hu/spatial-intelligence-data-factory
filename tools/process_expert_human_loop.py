from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from tools.process_compiler import ProcessCompiler
from tools.process_tools.design_process_tool import DesignProcessTool
from tools.process_tools.modify_process_tool import ModifyProcessTool


class InMemoryProcessRuntimeStore:
    def __init__(self) -> None:
        self._drafts: Dict[str, Dict[str, Any]] = {}
        self._process_defs: Dict[str, Dict[str, Any]] = {}

    def upsert_process_draft(self, **kwargs: Any) -> Dict[str, Any]:
        draft_id = str(kwargs.get("draft_id") or f"draft_{uuid.uuid4().hex[:10]}")
        self._drafts[draft_id] = dict(kwargs)
        return {
            "draft_id": draft_id,
            "updated_at": datetime.now().isoformat(),
            "status": kwargs.get("status", "editable"),
        }

    def find_process_definition(self, code: str) -> Optional[Dict[str, Any]]:
        return self._process_defs.get(str(code or "").upper())

    def ensure_process_definition(self, code: str, name: str, domain: str) -> Dict[str, Any]:
        final_code = str(code or "").upper()
        hit = self._process_defs.get(final_code)
        if hit:
            return hit
        item = {
            "id": f"procdef_{uuid.uuid4().hex[:12]}",
            "code": final_code,
            "name": name,
            "domain": domain,
        }
        self._process_defs[final_code] = item
        return item


@dataclass
class HumanLoopRunArtifacts:
    run_id: str
    run_dir: Path
    design_result: Dict[str, Any]
    decision_template: Dict[str, Any]
    modified_result: Optional[Dict[str, Any]]
    summary: Dict[str, Any]


class ProcessExpertHumanLoopRunner:
    def __init__(self, llm_service: Any, output_dir: Path) -> None:
        self.llm_service = llm_service
        self.output_dir = output_dir
        self.runtime_store = InMemoryProcessRuntimeStore()
        self.compiler = ProcessCompiler()
        self.design_tool = DesignProcessTool(
            runtime_store=self.runtime_store,
            process_compiler=self.compiler,
            llm_service=self.llm_service,
        )
        self.modify_tool = ModifyProcessTool(
            runtime_store=self.runtime_store,
            process_compiler=self.compiler,
            llm_service=self.llm_service,
        )

    def run(
        self,
        requirement: str,
        process_code: str = "",
        process_name: str = "",
        domain: str = "verification",
        decision_payload: Optional[Dict[str, Any]] = None,
    ) -> HumanLoopRunArtifacts:
        if not str(requirement or "").strip():
            raise ValueError("requirement 不能为空")

        run_id = f"human_loop_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run_dir = self.output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        design_result = self.design_tool.execute(
            {
                "requirement": requirement,
                "process_code": process_code,
                "process_name": process_name,
                "domain": domain,
                "goal": "人工主导设计，LLM提供草案与改进建议",
            },
            session_id=f"{run_id}_design",
        )
        if design_result.get("status") != "ok":
            raise RuntimeError(f"design failed: {design_result}")

        self.runtime_store.ensure_process_definition(
            code=str(design_result.get("process_code") or process_code),
            name=str(design_result.get("process_name") or process_name or "工艺草案"),
            domain=str(design_result.get("domain") or domain),
        )

        decision_template = self._build_decision_template(design_result)
        (run_dir / "design_result.json").write_text(
            json.dumps(design_result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (run_dir / "human_decision_template.json").write_text(
            json.dumps(decision_template, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        modified_result: Optional[Dict[str, Any]] = None
        if isinstance(decision_payload, dict):
            change_request = str(decision_payload.get("change_request") or "").strip()
            if change_request:
                modified_result = self.modify_tool.execute(
                    {
                        "process_code": str(design_result.get("process_code") or "").upper(),
                        "change_request": change_request,
                        "goal": str(decision_payload.get("goal") or "人工决策后的增量优化"),
                    },
                    session_id=f"{run_id}_modify",
                )
                (run_dir / "modified_result.json").write_text(
                    json.dumps(modified_result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

        summary = {
            "status": "ok",
            "mode": "human_llm_semi_auto",
            "run_id": run_id,
            "run_dir": str(run_dir),
            "requires_human_decision": True,
            "decision_applied": bool(isinstance(decision_payload, dict) and str(decision_payload.get("change_request") or "").strip()),
            "process_code": design_result.get("process_code"),
            "draft_id": design_result.get("draft_id"),
            "next_step": "填写 human_decision_template.json 后，以 --decision-file 再运行一次。",
        }
        (run_dir / "final_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return HumanLoopRunArtifacts(
            run_id=run_id,
            run_dir=run_dir,
            design_result=design_result,
            decision_template=decision_template,
            modified_result=modified_result,
            summary=summary,
        )

    @staticmethod
    def _build_decision_template(design_result: Dict[str, Any]) -> Dict[str, Any]:
        plan = dict(design_result.get("plan") or {})
        return {
            "decision": "hold",
            "reviewer": "",
            "review_notes": "",
            "risk_items": [],
            "change_request": "",
            "goal": "",
            "publish_recommendation": "pending",
            "draft_snapshot": {
                "draft_id": design_result.get("draft_id"),
                "process_code": design_result.get("process_code"),
                "process_name": design_result.get("process_name"),
                "quality_threshold": plan.get("quality_threshold"),
                "priority": plan.get("priority"),
            },
            "instructions": [
                "decision 取值建议: approve/revise/reject/hold",
                "如需LLM继续优化，请填写 change_request，并再次运行脚本传入 --decision-file",
                "发布动作必须通过服务端确认门禁，不在本脚本中自动执行",
            ],
        }
