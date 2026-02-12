"""工艺专家服务。"""

from tools.factory_framework import ProcessSpec, ProcessStep, generate_id
from tools.factory_agents import ProcessExpert


class ProcessExpertService:
    """工艺专家服务：管理固定产线所需工艺规格。"""

    def __init__(self, expert: ProcessExpert):
        self.expert = expert

    def create_cleaning_spec(self) -> ProcessSpec:
        return ProcessSpec(
            process_id=generate_id("proc"),
            process_name="地址清洗工艺",
            steps=[ProcessStep.PARSING, ProcessStep.STANDARDIZATION, ProcessStep.VALIDATION],
            estimated_duration=1.0,
            required_workers=2,
            quality_rules={"min_quality_score": 0.85},
            resource_requirements={"cpu": "standard", "memory": "512MB"},
        )

    def create_graph_spec(self) -> ProcessSpec:
        return ProcessSpec(
            process_id=generate_id("proc"),
            process_name="地址转图谱工艺",
            steps=[ProcessStep.EXTRACTION, ProcessStep.FUSION, ProcessStep.VALIDATION],
            estimated_duration=1.0,
            required_workers=2,
            quality_rules={"min_quality_score": 0.85},
            resource_requirements={"cpu": "standard", "memory": "512MB"},
        )
