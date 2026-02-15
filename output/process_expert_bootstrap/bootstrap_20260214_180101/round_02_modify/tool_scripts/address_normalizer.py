"""
地址规范化器 - 自动生成
Domain: address_governance
"""

def normalize_address(address: str, **config) -> Dict[str, str]:
    """规范化地址"""

    original = address

    # 去空格
    if config.get('remove_spaces', True):
        address = address.replace(' ', '').replace('\u3000', '')

    # 去标点
    if config.get('remove_punctuation', True):
        punctuation = '，。；：''""（）【】{}、'
        for p in punctuation:
            address = address.replace(p, '')

    # 繁简转换（简化版）
    if config.get('simplified', True):
        simplified_map = {'號': '号', '館': '馆', '國': '国'}
        for trad, simp in simplified_map.items():
            address = address.replace(trad, simp)

    return {
        'original': original,
        'normalized': address,
        'changed': original != address
    }
