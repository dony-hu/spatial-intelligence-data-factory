"""
ToolGenerator - 为工艺步骤生成执行工具脚本
"""

import os
import json
import re
from typing import Dict, Any

from .tool_templates import validators, normalizers, segmenters, evaluators, persisters, generators


class ToolGenerator:
    """工具代码生成器"""

    # 步骤→生成器映射
    TOOL_GENERATORS = {
        'INPUT_VALIDATION': ('validators', validators.generate_address_validator),
        'ADDRESS_NORMALIZATION': ('normalizers', normalizers.generate_address_normalizer),
        'ADDRESS_SEGMENTATION': ('segmenters', segmenters.generate_address_segmenter),
        'QUALITY_CHECK': ('evaluators', evaluators.generate_quality_evaluator),
        'OUTPUT_PERSIST': ('persisters', persisters.generate_db_persister),
        'DATA_CLEANING': ('cleaners', validators.generate_data_cleaner),  # 复用
        'DATA_MATCHING': ('matchers', normalizers.generate_data_matcher),  # 复用
        'DATA_GENERATION': ('generators', generators.generate_data_generator),
    }

    def __init__(self):
        self.generated_tools_dir = 'tools/generated_tools'
        self.generated_observability_root = 'workpackages/bundles'
        os.makedirs(self.generated_tools_dir, exist_ok=True)
        os.makedirs(self.generated_observability_root, exist_ok=True)

    def generate_tool(self,
                     step_name: str,
                     domain: str,
                     parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成工具脚本

        Args:
            step_name: ProcessStep 名称，如 'INPUT_VALIDATION'
            domain: 工艺域，如 'address_governance'
            parameters: 工具参数

        Returns:
            {
                'status': 'generated' | 'requires_external' | 'error',
                'tool_name': str,
                'code': str (if generated),
                'file_path': str (if generated),
                'message': str,
                'required_libs': list (if requires_external),
                'solution': str (if requires_external),
                'recommendation': str (if error)
            }
        """

        if step_name not in self.TOOL_GENERATORS:
            return {
                'status': 'error',
                'tool_name': f'{step_name.lower()}_tool',
                'message': f'未知的步骤类型: {step_name}',
                'recommendation': '请检查步骤名称是否正确'
            }

        module_name, generator_func = self.TOOL_GENERATORS[step_name]

        try:
            # 调用生成器函数
            result = generator_func(domain=domain, parameters=parameters)

            if result['status'] == 'generated':
                # 保存到文件
                tool_name = result['tool_name']
                file_path = self._save_tool_script(
                    module_name=module_name,
                    tool_name=tool_name,
                    code=result['code']
                )

                return {
                    'status': 'generated',
                    'tool_name': tool_name,
                    'code': result['code'],
                    'file_path': file_path,
                    'message': f'工具 {tool_name} 已生成'
                }

            elif result['status'] == 'requires_external':
                return result  # 直接返回（包含 required_libs 和 solution）

            else:  # error
                return result

        except Exception as e:
            return {
                'status': 'error',
                'tool_name': f'{step_name.lower()}_tool',
                'message': f'工具生成异常: {str(e)}',
                'recommendation': '请检查生成器配置'
            }

    def _save_tool_script(self, module_name: str, tool_name: str, code: str) -> str:
        """
        保存工具脚本到文件

        Args:
            module_name: 模块名，如 'validators', 'normalizers'
            tool_name: 工具名，如 'address_validator'
            code: 生成的代码

        Returns:
            文件路径
        """

        # 创建目录结构
        module_dir = os.path.join(self.generated_tools_dir, module_name)
        os.makedirs(module_dir, exist_ok=True)

        # 保存文件
        file_path = os.path.join(module_dir, f'{tool_name}.py')

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)

        return file_path

    @staticmethod
    def _normalize_slug(raw: str) -> str:
        """Normalize string to filesystem-safe slug."""
        value = str(raw or "").strip().lower()
        value = value.replace(".", "-")
        value = re.sub(r"[^a-z0-9_-]+", "-", value)
        value = re.sub(r"-{2,}", "-", value).strip("-")
        return value or "unknown"

    @staticmethod
    def _build_error_code_catalog(steps: list) -> Dict[str, Dict[str, str]]:
        """
        Build step-level standard error codes.
        Example:
        {
          "INPUT_VALIDATION": {"error_code": "STEP_INPUT_VALIDATION_FAIL", "error_message": "..."}
        }
        """
        catalog: Dict[str, Dict[str, str]] = {}
        for step in steps or []:
            step_name = str(step.get("name") or "UNKNOWN").upper()
            step_desc = str(step.get("description") or step_name)
            catalog[step_name] = {
                "error_code": f"STEP_{step_name}_FAIL",
                "error_message": f"{step_desc} 执行失败",
            }
        return catalog

    def generate_observability_bundle(
        self,
        process_code: str,
        process_version: str,
        steps: list,
        domain: str,
    ) -> Dict[str, Any]:
        """
        Generate observability bundle under workpackages/bundles/<slug>/observability.
        """
        bundle_slug = f"{self._normalize_slug(process_code)}-{self._normalize_slug(process_version)}"
        bundle_dir = os.path.join(self.generated_observability_root, bundle_slug, "observability")
        os.makedirs(bundle_dir, exist_ok=True)

        error_catalog = self._build_error_code_catalog(steps)

        line_observe_path = os.path.join(bundle_dir, "line_observe.py")
        line_metrics_path = os.path.join(bundle_dir, "line_metrics.json")

        line_observe_code = self._build_line_observe_code(domain=domain, error_catalog=error_catalog)
        line_metrics = {
            "metrics": [
                "task_total",
                "task_success",
                "task_failed",
                "quality_pass_rate",
                "avg_task_latency_ms",
                "step_error_rate",
            ],
            "owner": "factory",
            "version": process_version,
            "domain": domain,
            "step_error_codes": error_catalog,
        }

        with open(line_observe_path, "w", encoding="utf-8") as f:
            f.write(line_observe_code)

        with open(line_metrics_path, "w", encoding="utf-8") as f:
            json.dump(line_metrics, f, ensure_ascii=False, indent=2)

        return {
            "status": "generated",
            "bundle_id": bundle_slug,
            "entrypoints": [line_observe_path, line_metrics_path],
            "step_error_codes": error_catalog,
        }

    @staticmethod
    def _build_line_observe_code(domain: str, error_catalog: Dict[str, Dict[str, str]]) -> str:
        payload = json.dumps(error_catalog, ensure_ascii=False, indent=2)
        return f'''"""L3 line observability entrypoint generated by factory."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

STEP_ERROR_CODE_CATALOG = {payload}


def observe_step(
    task_id: str,
    step_code: str,
    status: str,
    payload: Dict[str, Any],
    error_code: str = "",
    error_detail: str = "",
) -> Dict[str, Any]:
    """Return normalized step observation event with standard error code."""
    step_key = str(step_code or "").upper()
    default_code = (STEP_ERROR_CODE_CATALOG.get(step_key) or {{}}).get("error_code", "")
    final_error_code = error_code or (default_code if status == "failed" else "")
    return {{
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "step_code": step_code,
        "status": status,
        "error_code": final_error_code,
        "error_detail": error_detail,
        "payload": payload,
    }}


def aggregate_runtime_metrics(step_events: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate runtime step metrics including step_error_rate."""
    total_steps = len(step_events)
    failed_steps = sum(1 for event in step_events if str((event or {{}}).get("status") or "").lower() == "failed")
    step_error_rate = round(float(failed_steps) / float(total_steps), 6) if total_steps > 0 else 0.0

    by_step: Dict[str, Dict[str, Any]] = {{}}
    for event in step_events:
        row = event or {{}}
        step_key = str(row.get("step_code") or "UNKNOWN").upper()
        holder = by_step.setdefault(step_key, {{"total": 0, "failed": 0, "step_error_rate": 0.0}})
        holder["total"] += 1
        if str(row.get("status") or "").lower() == "failed":
            holder["failed"] += 1

    for holder in by_step.values():
        holder["step_error_rate"] = round(float(holder["failed"]) / float(holder["total"]), 6) if holder["total"] > 0 else 0.0

    return {{
        "timestamp": datetime.now().isoformat(),
        "domain": "{domain}",
        "step_total": total_steps,
        "step_failed": failed_steps,
        "step_error_rate": step_error_rate,
        "by_step": by_step,
    }}
'''
