from packages.factory_cli.session import FactorySession


def test_session_chat_returns_blocked_when_agent_unavailable(monkeypatch) -> None:
    session = FactorySession()
    monkeypatch.setattr(session, "_get_agent", lambda: None)

    result = session.chat("请生成地址治理 MVP 方案")
    assert result["status"] == "blocked"
    assert result["reason"] == "agent_unavailable"
    assert result["requires_user_confirmation"] is True


def test_session_generate_script_returns_blocked_when_agent_unavailable(monkeypatch) -> None:
    session = FactorySession()
    monkeypatch.setattr(session, "_get_agent", lambda: None)

    result = session.generate_governance_script("生成一个地址治理脚本")
    assert result["status"] == "blocked"
    assert result["reason"] == "agent_unavailable"
