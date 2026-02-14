"""
ToolGenerator - 为工艺步骤生成执行工具脚本
"""

import os
import json
import re
from typing import Dict, Any

from .tool_templates import validators, normalizers, segmenters, evaluators, persisters


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
    }

    def __init__(self):
        self.generated_tools_dir = 'tools/generated_tools'
        os.makedirs(self.generated_tools_dir, exist_ok=True)

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

    def generate_observability_bundle(
        self,
        process_code: str,
        process_version: str,
        steps: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate L3 observability bundle for a compiled process."""
        bundle_key = self._slugify(f"{process_code}-{process_version}")
        obs_dir = os.path.join(
            "workpackages",
            "bundles",
            bundle_key,
            "observability",
        )
        os.makedirs(obs_dir, exist_ok=True)

        observe_py_path = os.path.join(obs_dir, "line_observe.py")
        metrics_json_path = os.path.join(obs_dir, "line_metrics.json")

        step_error_codes = {
            step.get("name", ""): step.get("error_code", f"{step.get('name', 'STEP')}_FAILED")
            for step in steps
            if step.get("name")
        }

        observe_code = self._build_observe_code(step_error_codes)
        metrics_payload = {
            "metrics": [
                "task_total",
                "task_success",
                "task_failed",
                "quality_pass_rate",
                "avg_task_latency_ms",
            ],
            "step_error_codes": step_error_codes,
            "owner": "factory",
            "version": process_version,
        }

        with open(observe_py_path, "w", encoding="utf-8") as f:
            f.write(observe_code)
        with open(metrics_json_path, "w", encoding="utf-8") as f:
            json.dump(metrics_payload, f, ensure_ascii=False, indent=2)

        return {
            "generator": "factory_observability_generator",
            "entrypoints": [observe_py_path, metrics_json_path],
            "step_error_codes": step_error_codes,
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

    def _slugify(self, value: str) -> str:
        cleaned = value.strip().lower()
        cleaned = re.sub(r"[^a-z0-9._-]+", "-", cleaned)
        cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
        return cleaned or "process-v1.0.0"

    def _build_observe_code(self, step_error_codes: Dict[str, str]) -> str:
        return (
            '"""L3 line observability entrypoint generated by factory."""\n\n'
            "from __future__ import annotations\n\n"
            "from datetime import datetime\n"
            "from typing import Any, Dict\n\n"
            f"STEP_ERROR_CODES = {repr(step_error_codes)}\n\n\n"
            "def observe_step(task_id: str, step_code: str, status: str, payload: Dict[str, Any]) -> Dict[str, Any]:\n"
            '    """Return a normalized step observation event for line runtime."""\n'
            "    event = {\n"
            '        "timestamp": datetime.now().isoformat(),\n'
            '        "task_id": task_id,\n'
            '        "step_code": step_code,\n'
            '        "status": status,\n'
            '        "payload": payload,\n'
            "    }\n"
            '    if status != "PASS":\n'
            '        event["error_code"] = STEP_ERROR_CODES.get(step_code, f"{step_code}_FAILED")\n'
            "    return event\n"
        )
