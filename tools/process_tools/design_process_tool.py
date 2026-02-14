"""
DesignProcessTool - LLM-based process design with ProcessCompiler integration

Handles process design from user requirements, integrating with:
- LLM for requirement analysis and plan generation
- ProcessCompiler for metadata extraction and tool generation
- Runtime store for persistence
"""

from typing import Dict, Any, Optional, List, Tuple
import uuid
from dataclasses import dataclass, field
import json

from ..agent_framework import BaseTool, ToolSchema


@dataclass
class DesignProcessTool(BaseTool):
    """
    Tool for designing new process from requirements.

    Integrates with LLM to analyze requirements and generate process plan,
    then compiles the design into executable specification.
    """

    name: str = "design_process"
    description: str = "从用户需求设计工艺流程，包括LLM分析和编译验证"

    input_schema: ToolSchema = field(default_factory=lambda: ToolSchema(
        properties={
            "requirement": {
                "type": "string",
                "description": "工艺设计需求描述",
                "minLength": 1,
                "maxLength": 2000
            },
            "process_code": {
                "type": "string",
                "description": "工艺编码（可选，会自动生成）",
                "pattern": "^[A-Z0-9_]{1,32}$"
            },
            "process_name": {
                "type": "string",
                "description": "工艺名称（可选）",
                "maxLength": 100
            },
            "domain": {
                "type": "string",
                "description": "业务域",
                "enum": ["address_governance", "graph_modeling", "verification", "other"],
                "default": "address_governance"
            },
            "goal": {
                "type": "string",
                "description": "工艺目标（可选）",
                "maxLength": 500
            }
        },
        required=["requirement"],
        additionalProperties=False
    ))

    # Injected dependencies
    runtime_store: Any = None
    process_compiler: Any = None
    llm_service: Any = None

    def __init__(self, runtime_store: Optional[Any] = None, process_compiler: Optional[Any] = None,
                 llm_service: Optional[Any] = None):
        """Initialize DesignProcessTool with dependencies"""
        super().__init__()
        self.runtime_store = runtime_store
        self.process_compiler = process_compiler
        self.llm_service = llm_service

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate design process parameters.

        Args:
            params: Tool parameters

        Returns:
            (is_valid, error_list)
        """
        errors = []

        # requirement is required
        requirement = str(params.get("requirement", "")).strip()
        if not requirement:
            errors.append("缺少必要参数 requirement")
        elif len(requirement) < 10:
            errors.append("requirement 至少需要 10 个字符")
        elif len(requirement) > 2000:
            errors.append("requirement 超过 2000 字符限制")

        # Validate optional code format if provided
        code = str(params.get("process_code", "")).strip()
        if code and not self._is_valid_code(code):
            errors.append("process_code 格式无效，应为大写字母、数字、下划线的组合，1-32 个字符")

        # Validate domain
        domain = str(params.get("domain", "address_governance")).strip()
        valid_domains = ["address_governance", "graph_modeling", "verification", "other"]
        if domain not in valid_domains:
            errors.append(f"domain 无效，应为 {', '.join(valid_domains)}")

        # Validate name if provided
        name = str(params.get("process_name", "")).strip()
        if name and len(name) > 100:
            errors.append("process_name 超过 100 字符限制")

        # Validate goal if provided
        goal = str(params.get("goal", "")).strip()
        if goal and len(goal) > 500:
            errors.append("goal 超过 500 字符限制")

        return (len(errors) == 0, errors if errors else None)

    def execute(self, params: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute process design tool.

        Args:
            params: Validated parameters
            session_id: Current session ID

        Returns:
            {
                "status": "ok" | "error",
                "draft_id": str,
                "process_code": str,
                "process_name": str,
                "plan": dict,
                "process_doc_markdown": str,
                "compilation": {...},
                "error": str (if error)
            }
        """
        try:
            # Extract parameters
            requirement = str(params.get("requirement", "")).strip()
            process_code = str(params.get("process_code", "")).strip()
            process_name = str(params.get("process_name", "")).strip()
            domain = str(params.get("domain", "address_governance")).strip()
            goal = str(params.get("goal", "")).strip()

            # Generate code if not provided
            if not process_code:
                process_code = self._generate_process_code(process_name or requirement)

            # Generate name if not provided
            if not process_name:
                process_name = f"{process_code} 工艺"

            # Generate draft ID
            draft_id = f"draft_{uuid.uuid4().hex[:10]}"

            # Call LLM for plan generation
            plan = self._generate_plan_from_requirement(requirement)

            # Generate process documentation
            process_doc = self._generate_process_documentation(
                process_code, process_name, requirement, goal, plan
            )

            # Create draft object
            draft = {
                "draft_id": draft_id,
                "requirement": requirement,
                "process_code": process_code,
                "process_name": process_name,
                "domain": domain,
                "goal": goal or requirement,
                "plan": plan,
                "process_doc_markdown": process_doc,
                "created_at": self._now_iso(),
            }

            # Persist to database
            if self.runtime_store:
                persisted = self.runtime_store.upsert_process_draft(
                    draft_id=draft_id,
                    session_id=session_id or "",
                    process_code=process_code,
                    process_name=process_name,
                    domain=domain,
                    requirement=requirement,
                    goal=goal or requirement,
                    plan=plan,
                    process_doc_markdown=process_doc,
                    status="editable",
                )
                draft.update({
                    "updated_at": persisted.get("updated_at"),
                    "draft_status": persisted.get("status", "editable")
                })

            # Compile process if compiler available
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
                "process_name": process_name,
                "domain": domain,
                "requirement": requirement,
                "goal": goal or requirement,
                "plan": plan,
                "process_doc_markdown": process_doc,
                "created_at": draft.get("created_at"),
                "updated_at": draft.get("updated_at"),
                "draft_status": draft.get("draft_status", "editable")
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
        """Check if code matches pattern: [A-Z0-9_]{1,32}"""
        if not code or len(code) < 1 or len(code) > 32:
            return False
        return all(c.isupper() or c.isdigit() or c == '_' for c in code)

    def _generate_process_code(self, source_name: str) -> str:
        """Generate process code from name or requirement"""
        import time
        # Extract uppercase letters and numbers
        code_base = "".join([c for c in source_name if c.isalnum() or c == '_'])[:15].upper()
        if not code_base:
            code_base = "PROC"
        # Add timestamp to ensure uniqueness
        timestamp_suffix = str(int(time.time() * 1000) % 100000)[-5:]
        return f"{code_base}_{timestamp_suffix}"

    def _generate_plan_from_requirement(self, requirement: str) -> Dict[str, Any]:
        """Call LLM to generate plan from requirement"""
        # This would integrate with the actual LLM service
        # For now, return a default plan structure
        if self.llm_service:
            try:
                # Call actual LLM service
                response = self.llm_service.generate_plan(requirement)
                return response.get("plan", {})
            except Exception:
                pass

        # Fallback default plan
        return {
            "auto_execute": False,
            "max_duration_sec": 300,
            "quality_threshold": 0.8,
            "priority": "normal",
            "steps": [
                "输入接入与标准化",
                "规则执行与门禁判定",
                "输出结构化JSON与证据登记"
            ]
        }

    def _generate_process_documentation(self, code: str, name: str,
                                       requirement: str, goal: str,
                                       plan: Dict[str, Any]) -> str:
        """Generate markdown documentation for the process"""
        steps = plan.get("steps", [])
        steps_md = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])

        return "\n".join([
            f"# 工艺流程文档：{name}",
            "",
            f"- **process_code**: `{code}`",
            f"- **requirement**: {requirement}",
            f"- **goal**: {goal}",
            f"- **auto_execute**: {plan.get('auto_execute', False)}",
            f"- **max_duration_sec**: {plan.get('max_duration_sec', 300)}",
            f"- **quality_threshold**: {plan.get('quality_threshold', 0.8)}",
            "",
            "## 步骤",
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
