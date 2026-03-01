#!/usr/bin/env python3
"""Compatibility facade for legacy factory demo server imports.

This module keeps the historical `tools.factory_simple_server` API surface used
by demo scripts/tests, while delegating the runtime state and web app to
`tools.factory_web_server`.
"""

from __future__ import annotations

import threading
from typing import Any, Callable

from tools.factory_web_server import app, factory_state

_action_handlers: dict[str, Callable[..., Any]] = {}


def register_action_handlers(handlers: dict[str, Callable[..., Any]]) -> None:
    """Register action callbacks for compatibility with legacy demo scripts."""
    _action_handlers.clear()
    _action_handlers.update(handlers or {})


def start_server(host: str = "127.0.0.1", port: int = 5000) -> threading.Thread:
    """Start Flask dashboard server in a daemon thread."""

    def _run() -> None:
        app.run(debug=False, host=host, port=port, threaded=True)

    thread = threading.Thread(target=_run, name=f"factory-web-{host}:{port}", daemon=True)
    thread.start()
    return thread


def main() -> int:
    print("[info] Starting compatibility dashboard server on 127.0.0.1:5000")
    start_server("127.0.0.1", 5000)
    try:
        while True:
            thread = threading.Event()
            thread.wait(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
