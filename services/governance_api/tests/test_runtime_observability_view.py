from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app


def test_runtime_observability_view_renders_runtime_sections() -> None:
    client = TestClient(app)
    resp = client.get("/v1/governance/observability/runtime/view?window=24h")
    assert resp.status_code == 200
    body = resp.text
    assert "系统运行态可观测总览" in body
    assert "任务总数" in body
    assert "完成率" in body
    assert "阻塞率" in body
    assert "平均置信度" in body
    assert "阻塞原因 Top5" in body
    assert "低置信模式 Top5" in body
    assert "可靠性-可用性" in body
    assert "SLO违约项" in body
    assert "质量漂移异常数" in body
    assert "聚合查询耗时" in body
    assert "上传地址批次并执行任务" in body
    assert "uploadFile" in body
    assert "已加载文件" in body
    assert "新增治理包链路观测" in body
    assert "workpackageRows" in body
    assert "wpModalMask" in body
    assert "任务详情（批次）" in body
    assert "modalMask" in body
