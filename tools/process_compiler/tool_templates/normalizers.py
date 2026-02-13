"""
规范化器工具模板
"""

from typing import Dict, Any


def generate_address_normalizer(domain: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """生成地址规范化工具"""

    code = f'''"""
地址规范化器 - 自动生成
Domain: {domain}
"""

def normalize_address(address: str, **config) -> Dict[str, str]:
    """规范化地址"""

    original = address

    # 去空格
    if config.get('remove_spaces', True):
        address = address.replace(' ', '').replace('\\u3000', '')

    # 去标点
    if config.get('remove_punctuation', True):
        punctuation = '，。；：''""（）【】{{}}、'
        for p in punctuation:
            address = address.replace(p, '')

    # 繁简转换（简化版）
    if config.get('simplified', True):
        simplified_map = {{'號': '号', '館': '馆', '國': '国'}}
        for trad, simp in simplified_map.items():
            address = address.replace(trad, simp)

    return {{
        'original': original,
        'normalized': address,
        'changed': original != address
    }}
'''

    return {
        'status': 'generated',
        'tool_name': 'address_normalizer',
        'code': code,
        'message': '规范化工具已生成'
    }


def generate_data_matcher(domain: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """生成数据匹配工具"""

    code = f'''"""
数据匹配器 - 自动生成
Domain: {domain}
"""

from difflib import SequenceMatcher

def match_data(source: str, target: str, threshold: float = 0.8) -> Dict[str, Any]:
    """匹配两个数据项的相似度"""

    ratio = SequenceMatcher(None, source, target).ratio()
    matched = ratio >= threshold

    return {{
        'source': source,
        'target': target,
        'similarity': ratio,
        'matched': matched,
        'threshold': threshold
    }}
'''

    return {
        'status': 'generated',
        'tool_name': 'data_matcher',
        'code': code,
        'message': '匹配工具已生成'
    }
