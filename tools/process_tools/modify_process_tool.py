"""
ModifyProcessTool - Modify existing process design

Allows users to request changes to an existing process definition,
generating a new draft based on the current process and modification request.
"""

from typing import Dict, Any, Optional, List, Tuple
import uuid
from dataclasses import dataclass, field

from ..agent_framework import BaseTool, ToolSchema


@dataclass
class ModifyProcessTool(BaseTool):
    """
    Tool for modifying existing process design.

    Takes a process definition and applies changes based on user request,
    creating a new design draft for the modified process.
    """

    name: str = "modify_process"
    description: str = "修改现有工艺流程定义"

    input_schema: ToolSchema = field(default_factory=lambda: ToolSchema(
        properties={
            "process_code": {
                "type": "string",
                "description": "待修改工艺编码",
                "pattern": "^[A-Z0-9_]{1,32}$"
            },
            "change_request": {
                "type": "string",
                "description": "修改内容说明",
                "minLength": 5,
                "maxLength": 1000
            },
            "goal": {
                "type": "string",
                "description": "修改目标（可选）",
                "maxLength": 500
            }
        },
        required=["process_code", "change_request"],
        additionalProperties=False
    ))

    # Injected dependencies
    runtime_store: Any = None
    process_compiler: Any = None
    llm_service: Any = None

    def __init__(self, runtime_store: Optional[Any] = None, process_compiler: Optional[Any] = None,
                 llm_service: Optional[Any] = None):
        """Initialize ModifyProcessTool with dependencies"""
        super().__init__()
        self.runtime_store = runtime_store
        self.process_compiler = process_compiler
        self.llm_service = llm_service

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate modify process parameters.

        Args:
            params: Tool parameters

        Returns:
            (is_valid, error_list)
        """
        errors = []

        # process_code is required
        process_code = str(params.get("process_code", "")).strip()
        if not process_code:
            errors.append("缺少必要参数 process_code")
        elif not self._is_valid_code(process_code):
            errors.append("process_code 格式无效")

        # change_request is required
        change_request = str(params.get("change_request", "")).strip()
        if not change_request:
            errors.append("缺少必要参数 change_request")
        elif len(change_request) < 5:
            errors.append("change_request 至少需要 5 个字符")
        elif len(change_request) > 1000:
            errors.append("change_request 超过 1000 字符限制")

        # Validate goal if provided
        goal = str(params.get("goal", "")).strip()
        if goal and len(goal) > 500:
            errors.append("goal 超过 500 字符限制")

        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute process modification tool.

        Args:
            params: Validated parameters
            session_id: Current session ID

        Returns:
            {
                "status": "ok" | "error",
                "draft_id": str,
                "process_code": str,
                "base_process_id": str,
                "change_request": str,
                "compilation": {...},
                "error": str (if error)
            }
        """
        try:
            process_code = str(params.get("process_code", "")).strip().upper()
            change_request = str(params.get("change_request", "")).strip()
            goal = str(params.get("goal", "")).strip()

            # Find existing process definition
            if not self.runtime_store:
                return {
                    "status": "error",
                    "error": "Runtime store not available",
                    "error_type": "service_error"
                }

            target_process = self.runtime_store.find_process_definition(code=process_code)
            if not target_process:
                return {
                    "status": "error",
                    "error": f"未找到工艺编码: {process_code}",
                    "error_type": "not_found"
                }

            # Generate requirement for modification
            base_name = target_process.get("name", process_code)
            requirement = f"请在已有工艺 {process_code} ({base_name}) 基础上完成如下变更：{change_request}"

            # Generate draft ID
            draft_id = f"draft_{uuid.uuid4().hex[:10]}"

            # Call LLM for modified plan
            plan = self._generate_modified_plan(requirement)

            # Generate updated documentation
            process_doc = self._generate_modified_documentation(
                process_code, base_name, change_request, goal, plan
            )

            # Create draft object
            draft = {
                "draft_id": draft_id,
                "requirement": requirement,
                "process_code": process_code,
                "process_name": base_name,
                "domain": target_process.get("domain", "address_governance"),
                "goal": goal or change_request,
                "plan": plan,
                "process_doc_markdown": process_doc,
                "base_process_definition_id": target_process.get("id"),
                "created_at": self._now_iso(),
            }

            # Persist to database
            persisted = self.runtime_store.upsert_process_draft(
                draft_id=draft_id,
                session_id=session_id or "",
                process_code=process_code,
                process_name=base_name,
                domain=target_process.get("domain", "address_governance"),
                requirement=requirement,
                goal=goal or change_request,
                plan=plan,
                process_doc_markdown=process_doc,
                base_process_definition_id=target_process.get("id"),
                status="editable",
            )
            draft.update({
                "updated_at": persisted.get("updated_at"),
                "draft_status": persisted.get("status", "editable")
            })

            # Compile modified process
            compilation_result = None
            if self.process_compiler:
                try:
                    compilation_result = self.process_compiler.compile(draft, session_id=session_id or "")
                    compilation = {
                        "success": compilation_result.success,
                        "process_code": compilation_result.process_code,
                        "process_spec": compilation_result.process_spec,
                        "tool_scripts": compilation_result.tool_scripts,
                        "tool_metadata": compilation_result.tool_metadata,
                        "observability_bundle": compilation_result.observability_bundle,
                        "execution_readiness": compilation_result.execution_readiness,
                        "validation_errors": compilation_result.validation_errors,
                        "validation_warnings": compilation_result.validation_warnings,
                    }
                except Exception as e:
                    compilation = {
                        "success": False,
                        "error": str(e),
                        "process_code": process_code
                    }
            else:
                compilation = {"success": False, "error": "ProcessCompiler not available"}

            result = {
                "status": "ok",
                "draft_id": draft_id,
                "process_code": process_code,
                "process_name": base_name,
                "base_process_id": target_process.get("id"),
                "change_request": change_request,
                "goal": goal or change_request,
                "plan": plan,
                "process_doc_markdown": process_doc,
                "created_at": draft.get("created_at"),
                "updated_at": draft.get("updated_at"),
            }

            if compilation_result:
                result["compilation"] = compilation

            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": "execution_error"
            }

    def _is_valid_code(self, code: str) -> bool:
        """Check if code matches pattern"""
        if not code or len(code) < 1 or len(code) > 32:
            return False
        return all(c.isupper() or c.isdigit() or c == '_' for c in code)

    def _generate_modified_plan(self, requirement: str) -> Dict[str, Any]:
        """Generate modified plan from requirement"""
        if self.llm_service:
            try:
                response = self.llm_service.generate_plan(requirement)
                return response.get("plan", {})
            except Exception:
                pass

        # Fallback
        return {
            "auto_execute": False,
            "max_duration_sec": 300,
            "quality_threshold": 0.8,
            "priority": "normal",
            "steps": ["应用修改后的规则", "验证修改结果"]
        }

    def _generate_modified_documentation(self, code: str, name: str,
                                        change_request: str, goal: str,
                                        plan: Dict[str, Any]) -> str:
        """Generate documentation for modified process"""
        steps = plan.get("steps", [])
        steps_md = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])

        return "\n".join([
            f"# 工艺流程文档：{name}（修改版）",
            "",
            f"- **process_code**: `{code}`",
            f"- **change_request**: {change_request}",
            f"- **goal**: {goal}",
            f"- **auto_execute**: {plan.get('auto_execute', False)}",
            "",
            "## 修改步骤",
            "",
            steps_md,
            "",
            "## 配置信息",
            "",
            "| 配置项 | 值 |",
            "| ---- | ---- |",
            f"| 执行优先级 | {plan.get('priority', 'normal')} |",
            f"| 最大执行时长 | {plan.get('max_duration_sec', 300)}s |",
            f"| 质量阈值 | {plan.get('quality_threshold', 0.8)} |",
        ])

    @staticmethod
    def _now_iso() -> str:
        """Return current time in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
