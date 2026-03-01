import os

import pytest

from packages.address_core.pipeline import run


class _DummyTrustProvider:
    def query_admin_division(self, namespace: str, name: str, parent_hint=None):
        return [{"name": name, "namespace": namespace}]

    def query_road(self, namespace: str, name: str, adcode_hint=None):
        return [{"name": name, "namespace": namespace}, {"name": f"{name}A", "namespace": namespace}]

    def query_poi(self, namespace: str, name: str, adcode_hint=None, top_k: int = 5):
        return [{"name": name, "namespace": namespace}]


class _FailingTrustProvider:
    def query_admin_division(self, namespace: str, name: str, parent_hint=None):
        raise RuntimeError("trust_down")


def test_pipeline_appends_trust_query_evidence() -> None:
    os.environ["ADDRESS_TRUSTED_FENGTU_ENABLED"] = "0"
    outputs = run(
        records=[{"raw_id": "r-trust-1", "raw_text": "杭州市西湖区文三路90号"}],
        ruleset={"ruleset_id": "default", "trust_namespace": "system.trust.dev"},
        trust_provider=_DummyTrustProvider(),
    )
    evidence_items = outputs[0]["evidence"]["items"]
    trust_items = [item for item in evidence_items if item.get("step") == "trust_query"]
    assert any(item.get("domain") == "admin_division" for item in trust_items)
    assert any(item.get("domain") == "road" for item in trust_items)
    assert any(item.get("domain") == "poi" for item in trust_items)


def test_pipeline_blocks_when_trust_required_and_provider_fails() -> None:
    os.environ["ADDRESS_TRUSTED_FENGTU_ENABLED"] = "0"
    with pytest.raises(ValueError, match="blocked: trust enhancement failed"):
        run(
            records=[{"raw_id": "r-trust-2", "raw_text": "杭州市西湖区文三路90号"}],
            ruleset={"ruleset_id": "default", "require_trust_enhancement": True, "trust_namespace": "system.trust.dev"},
            trust_provider=_FailingTrustProvider(),
        )
