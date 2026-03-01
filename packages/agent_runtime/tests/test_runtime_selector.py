import os

import pytest

from packages.agent_runtime.runtime_selector import get_runtime


def test_runtime_selector_opencode_default() -> None:
    os.environ.pop("AGENT_RUNTIME", None)
    runtime = get_runtime()
    assert runtime.__class__.__name__ == "OpenCodeRuntime"


def test_runtime_selector_rejects_legacy() -> None:
    os.environ["AGENT_RUNTIME"] = "legacy"
    with pytest.raises(ValueError, match="unsupported runtime"):
        get_runtime()
