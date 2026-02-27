from packages.factory_agent.agent import FactoryAgent


def test_supplement_trust_hub_returns_capability_and_sample(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    agent = FactoryAgent()
    result = agent.supplement_trust_hub("高德")
    assert result["status"] == "ok"
    assert result["action"] == "supplement_trust_hub"
    assert result["capability"]["source_id"]
    assert result["sample"]["source_id"]
