"""
数据生成器 - 自动生成
Domain: address_governance
参数: {'use_llm': True, 'model': 'gpt-3.5', 'temperature': 0.7}
"""

from typing import Dict, Any


def generate_data(input_payload: Dict[str, Any], **config) -> Dict[str, Any]:
    """根据输入生成结构化数据。

    说明：
    - 默认返回规则生成结果
    - 如接入外部 LLM，可在此函数中替换实现
    """

    use_llm = bool(config.get("use_llm", True))
    model = str(config.get("model", "gpt-3.5"))
    temperature = float(config.get("temperature", 0.7))

    base = {
        "mode": "llm" if use_llm else "rule",
        "model": model,
        "temperature": temperature,
        "input": input_payload,
    }

    # 依赖外部推理服务：未配置时只返回能力状态，不伪造生成结果
    base["generated"] = {
        "status": "requires_external_generation_service",
        "summary": "external generation service is required",
    }

    return base
