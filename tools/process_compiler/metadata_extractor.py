"""
MetadataExtractor - 从工艺描述中提取元数据
"""

import re
from typing import Dict, Any


class MetadataExtractor:
    """元数据提取器"""

    # ���键词→编码映射
    CODE_MAPPING = {
        '地址': 'ADDR',
        '分词': 'SEGMENT',
        '分割': 'SEGMENT',
        '解析': 'PARSE',
        '标准化': 'NORMALIZE',
        '规范': 'NORMALIZE',
        '验证': 'VALIDATE',
        '核实': 'VERIFY',
        '质量': 'QUALITY',
        '评估': 'EVALUATE',
        '清洗': 'CLEAN',
        '去重': 'DEDUP',
        '匹配': 'MATCH',
        '关联': 'LINK',
        '图谱': 'GRAPH',
        '生成': 'GENERATE',
        '转换': 'CONVERT',
    }

    def extract(self, draft_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取工艺元数据

        Args:
            draft_dict: {
                requirement: str,
                process_name: str,
                process_code: str (可能为 None),
                goal: str,
                domain: str
            }

        Returns:
            {
                process_code: str,
                process_name: str,
                domain: str,
                goal: str,
                description: str,
                estimated_duration: int (分钟),
                quality_threshold: float,
                completeness_threshold: float,
                consistency_threshold: float,
                required_workers: int,
                memory_gb: int,
                timeout_sec: int,
                retry_count: int
            }
        """

        text = draft_dict.get('requirement', '') + ' ' + draft_dict.get('goal', '')

        # 提取工艺编码
        process_code = self._extract_process_code(
            draft_dict.get('process_code') or draft_dict.get('process_name') or text
        )

        # 提取工艺名称
        process_name = self._extract_process_name(
            draft_dict.get('process_name') or text
        )

        # 提取域
        domain = self._extract_domain(draft_dict.get('domain') or text)

        # 提取时间
        estimated_duration = self._extract_duration(text)

        # 提取质量阈值
        quality_threshold = self._extract_threshold(text, 'accuracy|precision|精度|准确')

        # 提取完整性阈值
        completeness_threshold = self._extract_threshold(text, 'completeness|完整|覆盖')

        # 提取一致性阈值
        consistency_threshold = self._extract_threshold(text, 'consistency|一致|稳定')

        # 提取其他参数
        required_workers = self._extract_number(text, 'worker|工人|并发|并行', 1, 1)
        memory_gb = self._extract_number(text, 'memory|内存|GB|G', 2, 1)
        timeout_sec = self._extract_number(text, 'timeout|超时|秒', 600, 60)
        retry_count = self._extract_number(text, 'retry|重试|次', 3, 1)

        return {
            'process_code': process_code,
            'process_name': process_name,
            'domain': domain,
            'goal': draft_dict.get('goal', ''),
            'description': draft_dict.get('requirement', ''),
            'estimated_duration': estimated_duration,
            'quality_threshold': quality_threshold,
            'completeness_threshold': completeness_threshold,
            'consistency_threshold': consistency_threshold,
            'required_workers': required_workers,
            'memory_gb': memory_gb,
            'timeout_sec': timeout_sec,
            'retry_count': retry_count
        }

    def _extract_process_code(self, text: str) -> str:
        """生成规范的工艺编码"""

        # 提取关键词
        keywords = []
        for key, code in self.CODE_MAPPING.items():
            if key in text:
                keywords.append(code)

        if keywords:
            # 去重并组合
            unique_keywords = []
            for kw in keywords:
                if kw not in unique_keywords:
                    unique_keywords.append(kw)
            base_code = '_'.join(unique_keywords[:3])  # 最多3个关键词
        else:
            # 如果没有匹配到关键词，使用工艺名称的首字母缩写
            base_code = ''.join([c.upper() for c in text if c.isalpha()][:6])
            if not base_code:
                base_code = 'PROC'

        # 添加版本号
        return f"{base_code}_V1"

    def _extract_process_name(self, text: str) -> str:
        """提取工艺名称"""
        # 取第一句话
        sentences = re.split(r'[。，,]', text)
        name = sentences[0].strip()
        # 去除"帮我设计...""请创建..."等前缀
        name = re.sub(r'^(帮我|请|为我|请为我)(设计|创建|开发|设置)', '', name)
        name = re.sub(r'的工艺$|工艺$', '', name)
        return name or '未命名工艺'

    def _extract_domain(self, text: str) -> str:
        """提取工艺域"""
        domain_mapping = {
            '地址': 'address_governance',
            '图谱': 'graph_modeling',
            '核实': 'verification',
            '验证': 'verification',
            '清洗': 'data_cleaning',
            '标准': 'data_normalization',
        }

        for key, domain in domain_mapping.items():
            if key in text:
                return domain

        return 'address_governance'  # 默认

    def _extract_duration(self, text: str, default: int = 60) -> int:
        """提取预计处理时间（返回分钟）"""
        # 匹配 "60秒" "1分钟" "30分" 等
        patterns = [
            (r'(\d+)秒', lambda m: max(1, int(m.group(1)) // 60)),
            (r'(\d+)分钟', lambda m: int(m.group(1))),
            (r'(\d+)分', lambda m: int(m.group(1))),
            (r'(\d+)小时', lambda m: int(m.group(1)) * 60),
        ]

        for pattern, converter in patterns:
            match = re.search(pattern, text)
            if match:
                return converter(match)

        return default

    def _extract_threshold(self, text: str, pattern_keywords: str, default: float = 0.9) -> float:
        """提取质量阈值"""
        # 匹配 "95%" "0.95" "95分" 等
        pattern = rf'({pattern_keywords})[：:]*([0-9.]+)%?'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            value = float(match.group(2))
            # 如果是百分比格式，转换为小数
            if value > 1:
                value = value / 100
            return min(1.0, max(0.0, value))

        return default

    def _extract_number(self, text: str, pattern_keywords: str, default: int = 1, min_val: int = 1) -> int:
        """提取数值"""
        pattern = rf'({pattern_keywords})[：:]*(\d+)'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return max(min_val, int(match.group(2)))

        return default
