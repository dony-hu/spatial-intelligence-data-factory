"""
ProcessValidator - 验证编译后的工艺规范
"""

from typing import Dict, Any, List


class ProcessValidator:
    """工艺规范验证器"""

    def validate(self, process_spec: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        验证工艺规范

        Args:
            process_spec: ProcessSpec 字典

        Returns:
            {
                'errors': [...],
                'warnings': [...]
            }
        """

        errors = []
        warnings = []

        # 验证基本字段
        errors.extend(self._validate_basic_fields(process_spec))

        # 验证步骤
        errors.extend(self._validate_steps(process_spec))

        # 验证参数
        errors.extend(self._validate_parameters(process_spec))

        # 验证工具
        warnings.extend(self._validate_tools(process_spec))

        return {
            'errors': errors,
            'warnings': warnings
        }

    def _validate_basic_fields(self, spec: Dict[str, Any]) -> List[str]:
        """验证基本字段"""

        errors = []
        required_fields = ['process_id', 'process_code', 'process_name', 'domain', 'steps']

        for field in required_fields:
            if field not in spec or not spec[field]:
                errors.append(f'缺少必填字段: {field}')

        return errors

    def _validate_steps(self, spec: Dict[str, Any]) -> List[str]:
        """验证步骤"""

        errors = []
        steps = spec.get('steps', [])

        if not steps:
            errors.append('工艺必须至少包含一个步骤')
            return errors

        # 检查步骤名称
        valid_step_names = [
            'INPUT_VALIDATION',
            'ADDRESS_NORMALIZATION',
            'ADDRESS_SEGMENTATION',
            'QUALITY_CHECK',
            'OUTPUT_PERSIST',
            'DATA_CLEANING',
            'DATA_MATCHING',
            'DATA_GENERATION'
        ]

        for step in steps:
            if 'name' not in step:
                errors.append('步骤缺少 name 字段')
            elif step['name'] not in valid_step_names:
                errors.append(f'未知的步骤类型: {step["name"]}')

            if 'tool_name' not in step:
                errors.append(f'步骤 {step.get("name")} 缺少 tool_name')

        # 检查是否有输出步骤
        has_output = any(s['name'] == 'OUTPUT_PERSIST' for s in steps)
        if not has_output:
            errors.append('工艺必须包含 OUTPUT_PERSIST 步骤来持久化结果')

        return errors

    def _validate_parameters(self, spec: Dict[str, Any]) -> List[str]:
        """验证参数"""

        errors = []

        # 验证时间
        duration = spec.get('estimated_duration', 0)
        if duration <= 0:
            errors.append(f'estimated_duration 必须 > 0，当前值: {duration}')

        # 验证工作人数
        workers = spec.get('required_workers', 0)
        if workers <= 0:
            errors.append(f'required_workers 必须 > 0，当前值: {workers}')

        # 验证质量规则
        quality_rules = spec.get('quality_rules', {})
        for key, value in quality_rules.items():
            if not isinstance(value, (int, float)):
                errors.append(f'质量规则 {key} 必须是数字，当前值: {value}')
            elif not (0 <= value <= 1):
                errors.append(f'质量规则 {key} 必须在 0-1 之间，当前值: {value}')

        return errors

    def _validate_tools(self, spec: Dict[str, Any]) -> List[str]:
        """验证工具"""

        warnings = []
        tools = spec.get('tools', [])

        if not tools:
            warnings.append('工艺没有指定任何工具')
            return warnings

        # 检查工具脚本是否完整
        tool_scripts = spec.get('tool_scripts', {})
        for tool in tools:
            if tool not in tool_scripts or not tool_scripts[tool]:
                warnings.append(f'工具 {tool} 的脚本未生成或为空')

        return warnings
