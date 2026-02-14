"""
质量评估器 - 自动生成
Domain: address_governance
参数: {'accuracy_threshold': 0.95, 'completeness_threshold': 0.9, 'consistency_threshold': 0.88}
"""

def evaluate_quality(output: Dict[str, Any], **config) -> Dict[str, Any]:
    """
    评估处理输出的质量

    评估指标:
    - accuracy: 准确率（0-1）
    - completeness: 完整率（0-1）
    - consistency: 一致性（0-1）
    """

    accuracy = output.get('accuracy', 1.0)
    completeness = output.get('completeness', 1.0)
    consistency = output.get('consistency', 1.0)

    # 加权评分
    weights = config.get('weights', {'accuracy': 0.5, 'completeness': 0.3, 'consistency': 0.2})
    overall_score = (
        accuracy * weights['accuracy'] +
        completeness * weights['completeness'] +
        consistency * weights['consistency']
    )

    # 阈值检查
    accuracy_threshold = config.get('accuracy_threshold', 0.95)
    completeness_threshold = config.get('completeness_threshold', 0.9)
    consistency_threshold = config.get('consistency_threshold', 0.88)

    passed = (
        accuracy >= accuracy_threshold and
        completeness >= completeness_threshold and
        consistency >= consistency_threshold
    )

    return {
        'accuracy': accuracy,
        'completeness': completeness,
        'consistency': consistency,
        'overall_score': overall_score,
        'passed': passed,
        'details': {
            'accuracy_threshold': accuracy_threshold,
            'completeness_threshold': completeness_threshold,
            'consistency_threshold': consistency_threshold
        }
    }
