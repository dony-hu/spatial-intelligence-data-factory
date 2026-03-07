from __future__ import annotations

import json
import os
import re
from time import perf_counter

import pytest

from packages.factory_agent.agent import FactoryAgent
from packages.factory_agent.nanobot_adapter import NanobotAdapter


def _should_run_real_llm() -> bool:
    return str(os.getenv("RUN_REAL_LLM_LATENCY_TEST", "0")).strip() == "1"


def _extract_json_object(answer: str) -> dict:
    text = str(answer or "").strip()
    if not text:
        raise AssertionError("llm answer is empty")
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        payload = json.loads(text)
    except Exception:
        matched = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not matched:
            raise
        payload = json.loads(matched.group(0))
    if not isinstance(payload, dict):
        raise AssertionError("llm answer is not a json object")
    return payload


def test_real_llm_nanobot_chat_response_and_latency_under_10s(monkeypatch) -> None:
    if not _should_run_real_llm():
        pytest.skip("set RUN_REAL_LLM_LATENCY_TEST=1 to run real LLM latency guard")
    monkeypatch.setenv("LLM_TIMEOUT_SEC", "10")

    adapter = NanobotAdapter()
    started = perf_counter()
    result = adapter.chat(
        "请仅回复：OK",
        system_prompt="你是连通性探针，请只输出OK",
        max_tokens=16,
        temperature=0.0,
        timeout_sec=10,
    )
    elapsed = perf_counter() - started

    assert str(result.get("status") or "") == "ok"
    answer = str(result.get("answer") or "").strip()
    print(f"[real-llm] nanobot.chat elapsed={elapsed:.3f}s answer={answer[:120]!r}")
    assert answer
    assert "ok" in answer.lower()
    assert elapsed <= 10.0


def test_real_llm_nanobot_structured_json_and_latency_under_10s(monkeypatch) -> None:
    if not _should_run_real_llm():
        pytest.skip("set RUN_REAL_LLM_LATENCY_TEST=1 to run real LLM latency guard")
    monkeypatch.setenv("LLM_TIMEOUT_SEC", "10")

    adapter = NanobotAdapter()
    started = perf_counter()
    result = adapter.query_structured(
        "地址治理任务：输入地址列表，输出标准化与验真结果。",
        system_prompt=(
            "你是地址治理需求确认器。"
            "只输出一个紧凑JSON对象，字段必须包含target,data_sources,rule_points,outputs。"
            "每个数组仅输出1-2个短词，不要解释文本。"
        ),
        max_tokens=96,
        temperature=0.0,
        timeout_sec=10,
    )
    elapsed = perf_counter() - started
    payload = _extract_json_object(str(result.get("answer") or ""))
    print(
        "[real-llm] nanobot.query_structured elapsed="
        f"{elapsed:.3f}s target={str(payload.get('target') or '')[:80]!r}"
    )

    assert str(result.get("status") or "") == "ok"
    assert str(payload.get("target") or "").strip()
    assert isinstance(payload.get("data_sources"), list) and payload.get("data_sources")
    assert isinstance(payload.get("rule_points"), list) and payload.get("rule_points")
    assert isinstance(payload.get("outputs"), list) and payload.get("outputs")
    assert elapsed <= 10.0


def test_real_llm_factory_agent_general_chat_under_10s(monkeypatch) -> None:
    if not _should_run_real_llm():
        pytest.skip("set RUN_REAL_LLM_LATENCY_TEST=1 to run real LLM latency guard")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("FACTORY_AGENT_GENERAL_CHAT_TIMEOUT_SEC", "10")

    agent = FactoryAgent()
    started = perf_counter()
    result = agent.converse("请给我一句地址治理建议")
    elapsed = perf_counter() - started
    print(
        "[real-llm] factory_agent.general_chat elapsed="
        f"{elapsed:.3f}s reply={str(result.get('reply') or result.get('message') or '')[:120]!r}"
    )

    assert str(result.get("status") or "") == "ok"
    assert str(result.get("action") or "") == "general_governance_chat"
    assert str(result.get("message") or "").strip()
    assert elapsed <= 10.0


def test_real_llm_factory_agent_requirement_query_under_10s(monkeypatch) -> None:
    if not _should_run_real_llm():
        pytest.skip("set RUN_REAL_LLM_LATENCY_TEST=1 to run real LLM latency guard")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("FACTORY_AGENT_REQUIREMENT_TIMEOUT_SEC", "10")

    agent = FactoryAgent()
    started = perf_counter()
    result = agent._run_requirement_query("地址治理任务：输入地址列表，输出标准化与验真结果。")
    elapsed = perf_counter() - started
    summary = agent._extract_requirement_summary(str(result.get("answer") or ""))
    print(
        "[real-llm] factory_agent.requirement elapsed="
        f"{elapsed:.3f}s target={str(summary.get('target') or '')[:80]!r}"
    )

    assert str(result.get("status") or "") == "ok"
    assert str(summary.get("target") or "").strip()
    assert isinstance(summary.get("data_sources"), list) and summary.get("data_sources")
    assert isinstance(summary.get("rule_points"), list) and summary.get("rule_points")
    assert isinstance(summary.get("outputs"), list) and summary.get("outputs")
    assert elapsed <= 10.0
