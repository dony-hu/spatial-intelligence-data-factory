from __future__ import annotations

import random
import uuid
from typing import List, Dict, Any

from services.governance_api.app.models.task_models import TaskSubmitRequest, AddressRecordInput

class TestDataGenerator:
    @staticmethod
    def generate_task_submit_request(
        batch_size: int = 10,
        scenario: str = "clean"
    ) -> Dict[str, Any]:
        records = []
        for _ in range(batch_size):
            records.append(TestDataGenerator.generate_address_record(scenario))
        
        return TaskSubmitRequest(
            idempotency_key=str(uuid.uuid4()),
            batch_name=f"test_batch_{scenario}_{uuid.uuid4().hex[:8]}",
            ruleset_id="default",
            records=records
        ).model_dump()

    @staticmethod
    def generate_address_record(scenario: str = "clean") -> AddressRecordInput:
        raw_id = str(uuid.uuid4())
        
        if scenario == "clean":
            # Standard clean address
            return AddressRecordInput(
                raw_id=raw_id,
                raw_text="上海市浦东新区世纪大道100号",
                province=None,
                city=None,
                district=None,
                street=None,
                detail=None
            )
        elif scenario == "dirty":
            # Missing components, need cleaning
            return AddressRecordInput(
                raw_id=raw_id,
                raw_text="浦东新区世纪大道100号",
                province=None,
                city="上海市",
                district="浦东新区",
                street="世纪大道",
                detail="100号"
            )
        elif scenario == "malformed":
            # Malformed or extremely noisy data
            return AddressRecordInput(
                raw_id=raw_id,
                raw_text="   UNKNOWN_ADDRESS_#$@#   ",
                province=None,
                city=None,
                district=None,
                street=None,
                detail=None
            )
        elif scenario == "low_confidence":
             # Ambiguous address likely to trigger low confidence
            return AddressRecordInput(
                raw_id=raw_id,
                raw_text="人民路1号", # Ambiguous without city
                province=None,
                city=None,
                district=None,
                street="人民路",
                detail="1号"
            )
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
