from __future__ import annotations

import os

from packages.agent_runtime.adapters.legacy_runtime import LegacyRuntime
from packages.agent_runtime.adapters.opencode_runtime import OpenCodeRuntime


def get_runtime():
    runtime_name = os.getenv("AGENT_RUNTIME", "opencode").lower()
    if runtime_name == "legacy":
        if os.getenv("ALLOW_LEGACY_RUNTIME", "0") != "1":
            raise ValueError("legacy runtime disabled; set ALLOW_LEGACY_RUNTIME=1 to enable")
        return LegacyRuntime()
    if runtime_name != "opencode":
        raise ValueError(f"unsupported runtime: {runtime_name}")
    return OpenCodeRuntime()
