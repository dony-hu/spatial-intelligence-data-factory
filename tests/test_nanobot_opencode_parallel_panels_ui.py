from __future__ import annotations

from pathlib import Path


def test_nanobot_opencode_logs_use_parallel_panels_not_tabs() -> None:
    html = Path("web/dashboard/factory-agent-governance-prototype-v2.html").read_text(encoding="utf-8")
    assert "客户端 ↔ nanobot" in html
    assert "nanobot ↔ opencode" in html
    assert 'id="llmAccordion"' in html
    assert 'id="opencodeAccordion"' in html
    assert "status=" in html
    assert "结构化内容" in html
    assert "nav-tabs" not in html
