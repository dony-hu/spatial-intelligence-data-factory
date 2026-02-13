"""
ProcessCompiler - 将工艺草案编译为可执行的工艺规范
"""

import json
import uuid
import re
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .metadata_extractor import MetadataExtractor
from .step_identifier import StepIdentifier
from .tool_generator import ToolGenerator
from .validator import ProcessValidator


@dataclass
class CompileResult:
    """编译结果"""
    success: bool
    process_code: str
    process_name: str
    domain: str
    process_spec: Dict[str, Any]
    tool_scripts: Dict[str, str]                    # 工具名 → 代码
    tool_metadata: List[Dict[str, Any]]             # 工具信息和缺失告警
    validation_errors: List[str]
    validation_warnings: List[str]
    execution_readiness: str                        # "ready" | "partial" | "manual_required"

    def to_dict(self):
        return asdict(self)


class ProcessCompiler:
    """工艺编译器 - 核心编译逻辑"""

    def __init__(self):
        self.metadata_extractor = MetadataExtractor()
        self.step_identifier = StepIdentifier()
        self.tool_generator = ToolGenerator()
        self.validator = ProcessValidator()

    def compile(self,
                draft_dict: Dict[str, Any],
                session_id: str = "") -> CompileResult:
        """
        编译工艺草案

        Args:
            draft_dict: process_draft 数据
                {
                    draft_id: str,
                    requirement: str,
                    process_name: str,
                    domain: str,
                    goal: str,
                    process_doc_markdown: str
                }
            session_id: 会话ID

        Returns:
            CompileResult: 编译结果
        """
        errors = []
        warnings = []
        tool_scripts = {}
        tool_metadata = []

        try:
            # 步骤1: 提取元数据
            metadata = self._extract_metadata(draft_dict)
            process_code = metadata['process_code']
            process_name = metadata['process_name']
            domain = metadata['domain']

            # 步骤2: 识别工艺步骤
            steps = self._identify_steps(draft_dict)
            if not steps:
                errors.append("无法识别工艺步骤，请补充工艺描述")

            # 步骤3: 生成工具脚本
            for step in steps:
                step_name = step['name']
                result = self.tool_generator.generate_tool(
                    step_name=step_name,
                    domain=domain,
                    parameters=step.get('parameters', {})
                )

                if result['status'] == 'generated':
                    tool_scripts[result['tool_name']] = result['code']
                    tool_metadata.append({
                        'tool_name': result['tool_name'],
                        'step': step_name,
                        'status': 'generated',
                        'file_path': result['file_path']
                    })
                elif result['status'] == 'requires_external':
                    warnings.append(f"步骤 {step_name} 需要外部库: {result['message']}")
                    tool_metadata.append({
                        'tool_name': result['tool_name'],
                        'step': step_name,
                        'status': 'requires_external',
                        'required_libs': result.get('required_libs', []),
                        'message': result['message'],
                        'solution': result.get('solution', '')
                    })
                else:  # error
                    errors.append(f"步骤 {step_name} 工具生成失败: {result['message']}")
                    tool_metadata.append({
                        'tool_name': result['tool_name'],
                        'step': step_name,
                        'status': 'failed',
                        'error': result['message'],
                        'recommendation': result.get('recommendation', '')
                    })

            # 步骤4: 生成 ProcessSpec
            process_spec = self._build_process_spec(
                process_code=process_code,
                process_name=process_name,
                domain=domain,
                metadata=metadata,
                steps=steps,
                tool_scripts=tool_scripts
            )

            # 步骤5: 验证工艺
            validation_result = self.validator.validate(process_spec)
            errors.extend(validation_result['errors'])
            warnings.extend(validation_result['warnings'])

            # 确定执行就绪状态
            if errors:
                execution_readiness = "manual_required"  # 需要用户修复
            elif warnings:
                execution_readiness = "partial"  # 部分工具需要配置
            else:
                execution_readiness = "ready"  # 完全就绪

            return CompileResult(
                success=len(errors) == 0,
                process_code=process_code,
                process_name=process_name,
                domain=domain,
                process_spec=process_spec,
                tool_scripts=tool_scripts,
                tool_metadata=tool_metadata,
                validation_errors=errors,
                validation_warnings=warnings,
                execution_readiness=execution_readiness
            )

        except Exception as e:
            return CompileResult(
                success=False,
                process_code="UNKNOWN",
                process_name="未知工艺",
                domain="unknown",
                process_spec={},
                tool_scripts={},
                tool_metadata=[],
                validation_errors=[f"编译异常: {str(e)}"],
                validation_warnings=[],
                execution_readiness="manual_required"
            )

    def _extract_metadata(self, draft_dict: Dict[str, Any]) -> Dict[str, Any]:
        """提取工艺元数据"""
        return self.metadata_extractor.extract(draft_dict)

    def _identify_steps(self, draft_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别工艺步骤"""
        return self.step_identifier.identify(draft_dict)

    def _build_process_spec(self,
                           process_code: str,
                           process_name: str,
                           domain: str,
                           metadata: Dict[str, Any],
                           steps: List[Dict[str, Any]],
                           tool_scripts: Dict[str, str]) -> Dict[str, Any]:
        """构建 ProcessSpec"""

        process_id = f"procdef_{uuid.uuid4().hex[:12]}"
        process_version_id = f"procver_{uuid.uuid4().hex[:12]}"

        return {
            "process_id": process_id,
            "process_code": process_code,
            "process_name": process_name,
            "domain": domain,
            "version": "1.0.0",
            "version_id": process_version_id,
            "status": "draft",
            "created_at": datetime.now().isoformat(),

            # 步骤
            "steps": steps,

            # 资源需求
            "estimated_duration": metadata.get('estimated_duration', 60),  # 分钟
            "required_workers": metadata.get('required_workers', 1),

            # 质量规则
            "quality_rules": {
                "accuracy_threshold": metadata.get('quality_threshold', 0.9),
                "completeness_threshold": metadata.get('completeness_threshold', 0.85),
                "consistency_threshold": metadata.get('consistency_threshold', 0.88)
            },

            # 资源配置
            "resource_requirements": {
                "memory_gb": metadata.get('memory_gb', 2),
                "timeout_sec": metadata.get('timeout_sec', 600),
                "retry_count": metadata.get('retry_count', 3),
                "batch_size": metadata.get('batch_size', 1000)
            },

            # 工具清单
            "tools": list(tool_scripts.keys()),
            "tool_scripts": tool_scripts,

            # 其他
            "goal": metadata.get('goal', ''),
            "description": metadata.get('description', '')
        }
