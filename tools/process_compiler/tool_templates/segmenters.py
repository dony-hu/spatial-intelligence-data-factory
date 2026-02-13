"""
分词器工具模板
"""

from typing import Dict, Any


def generate_address_segmenter(domain: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """生成地址分词工具"""

    tokenizer_type = parameters.get('tokenizer', 'jieba')

    code = f'''"""
地址分词器 - 自动生成
Domain: {domain}
使用分词器: {tokenizer_type}
"""

def segment_address(address: str, **config) -> Dict[str, Any]:
    """
    分词地址

    注意: 需要安装依赖:
        pip install jieba  (if using jieba)
        pip install pylac  (if using LAC)
    """

    try:
        import jieba
        tokens = list(jieba.cut(address, cut_all=False))
    except ImportError:
        # 备用方案：简单的基于长度的分割
        tokens = [address[i:i+2] for i in range(0, len(address), 2)]

    return {{
        'address': address,
        'tokens': tokens,
        'token_count': len(tokens),
        'segments': ', '.join(tokens)
    }}


if __name__ == '__main__':
    test_addresses = [
        '北京市朝阳区建国门外大街1号',
        '上海市浦东新区张江高科技园区科苑路88号'
    ]

    for addr in test_addresses:
        result = segment_address(addr)
        print(f'{{addr}}')
        print(f'  分词: {{result["segments"]}}')
'''

    # 由于分词需要外部库，返回 requires_external
    return {
        'status': 'requires_external',
        'tool_name': 'address_segmenter',
        'code': code,
        'required_libs': ['jieba'],
        'message': '分词工具需要外部库支持',
        'solution': '''
分词工具需要以下库之一:

1. jieba（推荐，纯Python实现）
   pip install jieba

2. LAC（百度NLP）
   pip install pylac

3. HanLP（哈工大）
   pip install hanlp

或者配置现有NLP服务:
   API端点: http://nlp-service/segment
   方法: POST
   请求体: {{"text": "地址文本"}}
   响应: {{"tokens": [...]}}
'''
    }
