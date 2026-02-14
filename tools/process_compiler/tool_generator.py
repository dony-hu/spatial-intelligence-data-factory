"""
ToolGenerator - 为工艺步骤生成执行工具脚本
"""

import os
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
