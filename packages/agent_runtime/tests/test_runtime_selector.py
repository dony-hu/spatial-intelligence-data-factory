import os

from packages.agent_runtime.adapters.legacy_runtime import LegacyRuntime
from packages.agent_runtime.adapters.openhands_runtime import OpenHandsRuntime
from packages.agent_runtime.runtime_selector import get_runtime


def test_runtime_selector_openhands_default() -> None:
    os.environ.pop("AGENT_RUNTIME", None)
    runtime = get_runtime()
    assert isinstance(runtime, OpenHandsRuntime)


def test_runtime_selector_legacy() -> None:
    os.environ["AGENT_RUNTIME"] = "legacy"
    runtime = get_runtime()
    assert isinstance(runtime, LegacyRuntime)
