"""
地址验证器 - 自动生成
Domain: address_governance
参数: {'max_length': 200, 'required_fields': ['address'], 'allowed_formats': ['standard', 'simplified']}
"""

import re
from typing import Dict, List


class AddressValidator:
    """地址验证器"""

    def __init__(self, **config):
        self.max_length = config.get('max_length', 200)
        self.required_fields = config.get('required_fields', ['address'])
        self.allowed_formats = config.get('allowed_formats', ['standard'])

    def validate(self, data: Dict[str, str]) -> Dict[str, Any]:
        """验证地址数据"""

        errors = []
        warnings = []

        # 检查必填字段
        for field in self.required_fields:
            if field not in data or not data[field]:
                errors.append(f'缺少必填字段: {field}')

        if errors:
            return {'valid': False, 'errors': errors, 'score': 0.0}

        address = data.get('address', '').strip()

        # 长度检查
        if len(address) > self.max_length:
            errors.append(f'地址长度 {len(address)} 超过限制 {self.max_length}')

        if len(address) < 2:
            errors.append('地址过短（最少2字符）')

        # 字符检查
        cn_chars = sum(1 for c in address if ord(c) >= 0x4e00 and ord(c) <= 0x9fff)
        if cn_chars == 0:
            warnings.append('地址中没有中文字符')

        # 数字检查
        has_numbers = any(c.isdigit() for c in address)
        if not has_numbers:
            warnings.append('地址中没有数字')

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'address': address,
            'score': 1.0 - len(errors) * 0.5,
            'metadata': {
                'length': len(address),
                'chinese_chars': cn_chars,
                'has_numbers': has_numbers
            }
        }


def validate_address(address: str, **config) -> Dict[str, Any]:
    """快速验证函数"""
    validator = AddressValidator(**config)
    return validator.validate({'address': address})


if __name__ == '__main__':
    validator = AddressValidator()

    test_cases = [
        '北京市朝阳区建国门外大街1号',
        '上海市浦东新区张江高科技园区科苑路88号',
        '',
        'Test Address'
    ]

    for addr in test_cases:
        result = validate_address(addr)
        print(f'{addr[:30]:30} → {result["valid"]} ({result["score"]:.2f}/1.0)')
