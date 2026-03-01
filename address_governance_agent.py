#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地址治理Agent - 处理单个地址并生成治理建议
"""

import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from address_governance import AddressGovernanceSystem


def process_address_governance(task_context, ruleset):
    """
    处理地址治理任务并生成建议
    """
    # 初始化治理系统
    governance_system = AddressGovernanceSystem()

    # 提取输入地址
    records = task_context.get("records", [])
    if not records:
        return {
            "strategy": "error",
            "confidence": 0.0,
            "canonical": {},
            "actions": [{"type": "error", "description": "无地址记录"}],
            "evidence": {"items": [{"type": "error", "message": "输入为空"}]},
        }

    record = records[0]
    raw_address = record.get("raw_text", "")

    if not raw_address:
        return {
            "strategy": "error",
            "confidence": 0.0,
            "canonical": {},
            "actions": [{"type": "error", "description": "地址文本为空"}],
            "evidence": {"items": [{"type": "error", "message": "地址文本为空"}]},
        }

    # 处理地址
    try:
        result = governance_system.process_address(raw_address)

        # 分析结果确定治理策略
        parsed = result.get("parsed", {})
        standardized = result.get("standardized", {})
        quality_score = result.get("quality_score", 0.0)

        # 提取标准化后的地址成分
        province = standardized.get("province", "")
        city = standardized.get("city", "")
        district = standardized.get("district", "")
        street = standardized.get("street", "")

        # 确定治理策略
        if quality_score >= 0.85:
            strategy = "auto_accept"
        elif quality_score >= 0.7:
            strategy = "review_needed"
        else:
            strategy = "manual_review"

        # 构建canonical地址
        canonical = {
            "raw_id": record.get("raw_id"),
            "raw_address": raw_address,
            "standardized_address": standardized.get("standard_full_address", ""),
            "province": province,
            "city": city,
            "district": district,
            "street": street,
            "confidence": quality_score,
        }

        # 生成处理动作
        actions = []

        # 添加标准化动作
        rules_applied = standardized.get("rules_applied", [])
        for rule in rules_applied:
            actions.append(
                {
                    "type": "standardization",
                    "rule": rule,
                    "description": "应用标准化规则: " + str(rule),
                }
            )

        # 根据质量分数添加验证动作
        if quality_score < 0.8:
            actions.append(
                {
                    "type": "validation_needed",
                    "description": "质量分数"
                    + str(round(quality_score, 2))
                    + "低于阈值，需要验证",
                }
            )

        # 添加实体映射动作
        entity_mapping = result.get("entity_mapping", {})
        if entity_mapping.get("entity_id"):
            actions.append(
                {
                    "type": "entity_mapped",
                    "entity_id": entity_mapping.get("entity_id"),
                    "entity_type": entity_mapping.get("entity_type"),
                    "confidence": entity_mapping.get("match_confidence"),
                }
            )

        # 生成证据
        evidence_items = []

        # 添加解析证据
        components = parsed.get("components", {})
        for comp_type, value in components.items():
            if value:
                evidence_items.append(
                    {
                        "type": "parsed_component",
                        "component": comp_type,
                        "value": value,
                        "confidence": parsed.get("component_confidences", {}).get(
                            comp_type, 0.0
                        ),
                    }
                )

        # 添加处理过程证据
        evidence_items.append(
            {
                "type": "processing_metadata",
                "parsing_method": parsed.get("parsing_method"),
                "processing_region": result.get("processing_region"),
                "timestamp": result.get("timestamp"),
            }
        )

        # 添加质量评估证据
        evidence_items.append(
            {
                "type": "quality_assessment",
                "overall_quality": quality_score,
                "parsing_confidence": parsed.get("confidence_score", 0.0),
                "standardization_confidence": standardized.get("confidence_score", 0.0),
            }
        )

        return {
            "strategy": strategy,
            "confidence": quality_score,
            "canonical": canonical,
            "actions": actions,
            "evidence": {"items": evidence_items},
        }

    except Exception as e:
        return {
            "strategy": "error",
            "confidence": 0.0,
            "canonical": {},
            "actions": [{"type": "error", "description": "处理失败: " + str(e)}],
            "evidence": {"items": [{"type": "error", "message": str(e)}]},
        }


if __name__ == "__main__":
    # 从命令行参数读取输入
    if len(sys.argv) != 3:
        print(
            json.dumps(
                {
                    "strategy": "error",
                    "confidence": 0.0,
                    "canonical": {},
                    "actions": [{"type": "error", "description": "参数错误"}],
                    "evidence": {
                        "items": [
                            {
                                "type": "error",
                                "message": "需要task_context和ruleset参数",
                            }
                        ]
                    },
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    try:
        task_context = json.loads(sys.argv[1])
        ruleset = json.loads(sys.argv[2])

        result = process_address_governance(task_context, ruleset)
        print(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        print(
            json.dumps(
                {
                    "strategy": "error",
                    "confidence": 0.0,
                    "canonical": {},
                    "actions": [
                        {"type": "error", "description": "执行失败: " + str(e)}
                    ],
                    "evidence": {"items": [{"type": "error", "message": str(e)}]},
                },
                ensure_ascii=False,
            )
        )
