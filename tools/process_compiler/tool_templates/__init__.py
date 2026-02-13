"""
工具模板库 - 为不同的 ProcessStep 提供代码生成模板
"""

from typing import Dict, Any

__all__ = [
    'validators',
    'normalizers',
    'segmenters',
    'evaluators',
    'persisters'
]


# 简单的代码生成函数示例

def generate_validator_template(domain: str, parameters: Dict[str, Any]) -> str:
    """生成验证器模板代码"""

    return f'''"""
地址验证器 - 自动生成
Domain: {domain}
"""

def validate_address(address: str, **kwargs) -> dict:
    """验证地址格式和内容"""

    errors = []

    # 长度检查
    max_length = {parameters.get('max_length', 200)}
    if len(address) > max_length:
        errors.append(f'地址长度超过 {{max_length}}')

    if len(address) < 2:
        errors.append('地址过短')

    # 字符检查
    if not any(c.isalnum() or c in '省市区县街道号楼座单元堂' for c in address):
        errors.append('地址不包含有效字符')

    return {{
        'valid': len(errors) == 0,
        'errors': errors,
        'address': address,
        'score': 1.0 if not errors else 0.0
    }}


if __name__ == '__main__':
    # 测试
    test_cases = [
        '北京市朝阳区建国门外大街1号',
        '上海市浦东新区张江高科技园区科苑路88号',
        '',
        '太长' * 100
    ]

    for addr in test_cases:
        result = validate_address(addr)
        print(f'{{addr[:30]}}: {{result["valid"]}}')
'''


def generate_normalizer_template(domain: str, parameters: Dict[str, Any]) -> str:
    """生成规范化器模板代码"""

    return f'''"""
地址规范化器 - 自动生成
Domain: {domain}
"""

def normalize_address(address: str, **kwargs) -> dict:
    """规范化地址格式"""

    original = address

    # 去空格
    if {parameters.get('remove_spaces', True)}:
        address = address.replace(' ', '')

    # 去标点
    if {parameters.get('remove_punctuation', True)}:
        punctuation = '，。；：''""（）'
        for p in punctuation:
            address = address.replace(p, '')

    # 繁简转换
    if {parameters.get('simplified', True)}:
        # 简单繁简转换（实际应使用专业库）
        address = address.replace('號', '号')
        address = address.replace('館', '馆')

    return {{
        'original': original,
        'normalized': address,
        'score': 1.0,
        'changes': {{
            'removed_spaces': original != address and ' ' in original,
            'removed_punctuation': any(p in original for p in '，。；：''""（）'),
        }}
    }}


if __name__ == '__main__':
    test_cases = [
        '北京市 朝阳区 建国门外大街1号',
        '上海市，浦东新区；张江高科技园区（科苑路88号）',
    ]

    for addr in test_cases:
        result = normalize_address(addr)
        print(f'{{result["original"]}} → {{result["normalized"]}}')
'''
