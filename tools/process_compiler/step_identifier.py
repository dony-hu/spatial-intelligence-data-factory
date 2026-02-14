"""
StepIdentifier - 从工艺描述中识别处理步骤
"""

import re
from typing import List, Dict, Any


class StepIdentifier:
    """步骤识别器"""

    STEP_ERROR_CODES = {
        'INPUT_VALIDATION': 'INPUT_VALIDATION_FAILED',
        'ADDRESS_NORMALIZATION': 'ADDRESS_NORMALIZATION_FAILED',
        'ADDRESS_SEGMENTATION': 'ADDRESS_SEGMENTATION_FAILED',
        'QUALITY_CHECK': 'QUALITY_CHECK_FAILED',
        'OUTPUT_PERSIST': 'OUTPUT_PERSIST_FAILED',
        'DATA_CLEANING': 'DATA_CLEANING_FAILED',
        'DATA_MATCHING': 'DATA_MATCHING_FAILED',
        'DATA_GENERATION': 'DATA_GENERATION_FAILED',
    }

    # 步骤→工具映射
    STEP_DEFINITIONS = {
        'INPUT_VALIDATION': {
            'name': 'INPUT_VALIDATION',
            'description': '输入验证',
            'keywords': ['验证', '校验', '检查', '验证格式'],
            'tool_name': 'address_validator',
            'tool_module': 'validators.py',
            'parameters': {
                'max_length': 200,
                'required_fields': ['address'],
                'allowed_formats': ['standard', 'simplified']
            }
        },
        'ADDRESS_NORMALIZATION': {
            'name': 'ADDRESS_NORMALIZATION',
            'description': '地址标准化',
            'keywords': ['标准化', '规范化', '标准', '规范'],
            'tool_name': 'address_normalizer',
            'tool_module': 'normalizers.py',
            'parameters': {
                'remove_spaces': True,
                'remove_punctuation': True,
                'simplified': True,
                'lowercase': False
            }
        },
        'ADDRESS_SEGMENTATION': {
            'name': 'ADDRESS_SEGMENTATION',
            'description': '地址分词',
            'keywords': ['分词', '分割', '拆分', '解析'],
            'tool_name': 'address_segmenter',
            'tool_module': 'segmenters.py',
            'parameters': {
                'tokenizer': 'jieba',  # 或 'lac', 'hanlp'
                'remove_stop_words': True,
                'return_positions': True
            }
        },
        'QUALITY_CHECK': {
            'name': 'QUALITY_CHECK',
            'description': '质量评估',
            'keywords': ['质量', '评估', '评分', '打分', '检查质量'],
            'tool_name': 'quality_evaluator',
            'tool_module': 'evaluators.py',
            'parameters': {
                'accuracy_threshold': 0.95,
                'completeness_threshold': 0.9,
                'consistency_threshold': 0.88
            }
        },
        'OUTPUT_PERSIST': {
            'name': 'OUTPUT_PERSIST',
            'description': '结果持久化',
            'keywords': ['入库', '保存', '存储', '写入'],
            'tool_name': 'db_persister',
            'tool_module': 'persisters.py',
            'parameters': {
                'database': 'sqlite',
                'table_name': 'process_results',
                'batch_size': 1000
            }
        },
        'DATA_CLEANING': {
            'name': 'DATA_CLEANING',
            'description': '数据清洗',
            'keywords': ['清洗', '去重', '去噪', '清理'],
            'tool_name': 'data_cleaner',
            'tool_module': 'cleaners.py',
            'parameters': {
                'remove_duplicates': True,
                'remove_empty': True,
                'normalize_encoding': True
            }
        },
        'DATA_MATCHING': {
            'name': 'DATA_MATCHING',
            'description': '数据匹配',
            'keywords': ['匹配', '关联', '对齐', '映射'],
            'tool_name': 'data_matcher',
            'tool_module': 'matchers.py',
            'parameters': {
                'algorithm': 'fuzzy',
                'threshold': 0.8,
                'use_phonetic': False
            }
        },
        'DATA_GENERATION': {
            'name': 'DATA_GENERATION',
            'description': '数据生成',
            'keywords': ['生成', '创建', '构建'],
            'tool_name': 'data_generator',
            'tool_module': 'generators.py',
            'parameters': {
                'use_llm': True,
                'model': 'gpt-3.5',
                'temperature': 0.7
            }
        }
    }

    def identify(self, draft_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        识别工艺步骤

        Args:
            draft_dict: {
                requirement: str,
                process_doc_markdown: str,
                goal: str
            }

        Returns:
            [
                {
                    'step_index': 1,
                    'name': 'INPUT_VALIDATION',
                    'description': '输入验证',
                    'tool_name': 'address_validator',
                    'parameters': {...}
                },
                ...
            ]
        """

        # 合并所有文本
        full_text = (
            draft_dict.get('requirement', '') + ' ' +
            draft_dict.get('process_doc_markdown', '') + ' ' +
            draft_dict.get('goal', '')
        )

        identified_steps = []
        found_steps = set()

        # 依次匹配关键词
        for step_key, step_def in self.STEP_DEFINITIONS.items():
            for keyword in step_def['keywords']:
                if keyword in full_text and step_key not in found_steps:
                    identified_steps.append({
                        'step_index': len(identified_steps) + 1,
                        'name': step_def['name'],
                        'description': step_def['description'],
                        'tool_name': step_def['tool_name'],
                        'tool_module': step_def['tool_module'],
                        'parameters': step_def['parameters'],
                        'error_code': self._default_error_code(step_def['name']),
                    })
                    found_steps.add(step_key)
                    break

        # 如果没有识别到任何步骤，添加默认步骤
        if not identified_steps:
            identified_steps = [
                {
                    'step_index': 1,
                    'name': 'INPUT_VALIDATION',
                    'description': '输入验证',
                    'tool_name': 'address_validator',
                    'tool_module': 'validators.py',
                    'parameters': self.STEP_DEFINITIONS['INPUT_VALIDATION']['parameters'],
                    'error_code': self._default_error_code('INPUT_VALIDATION'),
                },
                {
                    'step_index': 2,
                    'name': 'ADDRESS_NORMALIZATION',
                    'description': '地址标准化',
                    'tool_name': 'address_normalizer',
                    'tool_module': 'normalizers.py',
                    'parameters': self.STEP_DEFINITIONS['ADDRESS_NORMALIZATION']['parameters'],
                    'error_code': self._default_error_code('ADDRESS_NORMALIZATION'),
                },
                {
                    'step_index': 3,
                    'name': 'QUALITY_CHECK',
                    'description': '质量评估',
                    'tool_name': 'quality_evaluator',
                    'tool_module': 'evaluators.py',
                    'parameters': self.STEP_DEFINITIONS['QUALITY_CHECK']['parameters'],
                    'error_code': self._default_error_code('QUALITY_CHECK'),
                }
            ]

        # 添加输出步骤（如果没有）
        if not any(s['name'] == 'OUTPUT_PERSIST' for s in identified_steps):
            identified_steps.append({
                'step_index': len(identified_steps) + 1,
                'name': 'OUTPUT_PERSIST',
                'description': '结果持久化',
                'tool_name': 'db_persister',
                'tool_module': 'persisters.py',
                'parameters': self.STEP_DEFINITIONS['OUTPUT_PERSIST']['parameters'],
                'error_code': self._default_error_code('OUTPUT_PERSIST'),
            })

        return identified_steps

    def _default_error_code(self, step_name: str) -> str:
        """Return default normalized error code for a step."""
        if step_name in self.STEP_ERROR_CODES:
            return self.STEP_ERROR_CODES[step_name]
        return f"{step_name}_FAILED"
