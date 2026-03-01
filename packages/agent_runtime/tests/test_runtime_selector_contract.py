import pytest

from packages.agent_runtime.runtime_selector import get_runtime


def test_runtime_selector_returns_opencode_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AGENT_RUNTIME", raising=False)
    runtime = get_runtime()
    assert runtime.__class__.__name__ == "OpenCodeRuntime"


def test_runtime_selector_rejects_unsupported_runtime(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME", "legacy")
    with pytest.raises(ValueError, match="unsupported runtime"):
        get_runtime()
