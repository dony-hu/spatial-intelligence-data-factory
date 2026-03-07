import pytest

from packages.factory_agent.agent import FactoryAgent


@pytest.fixture(autouse=True)
def _llm_env_for_factory_agent_tests(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test-for-unit")


def test_factory_agent_has_no_llm_gateway_member(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    assert not hasattr(agent, "_llm_gateway")


def test_run_requirement_query_calls_nanobot_adapter(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("FACTORY_AGENT_REQUIREMENT_TIMEOUT_SEC", "10")
    agent = FactoryAgent()
    captured = {}

    def _fake_query_structured(
        requirement,
        *,
        system_prompt="",
        session_key=None,
        max_tokens=None,
        temperature=None,
        timeout_sec=None,
    ):
        captured["requirement"] = requirement
        captured["system_prompt"] = system_prompt
        captured["session_key"] = session_key
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        captured["timeout_sec"] = timeout_sec
        return {"status": "ok", "answer": "{}"}

    monkeypatch.setattr(agent._nanobot, "query_structured", _fake_query_structured)

    result = agent._run_requirement_query("请生成地址治理 MVP 方案")
    assert result["status"] == "ok"
    assert captured.get("requirement") == "请生成地址治理 MVP 方案"
    assert "target(字符串)" in str(captured.get("system_prompt") or "")
    assert str(captured.get("session_key") or "").startswith("factory_agent:requirement:")
    assert int(captured.get("max_tokens") or 0) == 96
    assert int(captured.get("timeout_sec") or 0) == 10


def test_run_general_chat_query_includes_recent_history(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("FACTORY_AGENT_GENERAL_CHAT_TIMEOUT_SEC", "10")
    agent = FactoryAgent()
    agent._append_chat_history("user", "第一轮")
    agent._append_chat_history("assistant", "收到")
    captured = {}

    def _fake_chat(prompt, *, system_prompt="", session_key=None, max_tokens=None, temperature=None, timeout_sec=None):
        captured["prompt"] = prompt
        captured["system_prompt"] = system_prompt
        captured["session_key"] = session_key
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        captured["timeout_sec"] = timeout_sec
        return {"status": "ok", "answer": "好的"}

    monkeypatch.setattr(agent._nanobot, "chat", _fake_chat)

    result = agent._run_general_chat_query("当前问题")
    assert result["status"] == "ok"
    assert "历史对话：" in str(captured.get("prompt") or "")
    assert "当前用户输入：" in str(captured.get("prompt") or "")
    assert "自然沟通" in str(captured.get("system_prompt") or "")
    assert str(captured.get("session_key") or "").startswith("factory_agent:chat:")
    assert int(captured.get("timeout_sec") or 0) == 10


def test_run_workpackage_blueprint_query_calls_nanobot_adapter_with_feedback(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("FACTORY_AGENT_BLUEPRINT_TIMEOUT_SEC", "10")
    agent = FactoryAgent()
    captured = {}

    def _fake_query_structured(
        requirement,
        *,
        system_prompt="",
        session_key=None,
        max_tokens=None,
        temperature=None,
        timeout_sec=None,
    ):
        captured["requirement"] = requirement
        captured["system_prompt"] = system_prompt
        captured["session_key"] = session_key
        captured["timeout_sec"] = timeout_sec
        return {"status": "ok", "answer": "{}"}

    monkeypatch.setattr(agent._nanobot, "query_structured", _fake_query_structured)
    result = agent._run_workpackage_blueprint_query(
        "创建工作包",
        context={"architecture_context": {"layers": ["x"]}},
        feedback=["schema_error: scripts[0].entry is required"],
    )

    assert result["status"] == "ok"
    assert "历史对话" not in str(captured.get("requirement") or "")
    assert "架构与API上下文" in str(captured.get("requirement") or "")
    assert "schema_error" in str(captured.get("requirement") or "")
    assert "最终必须输出一个JSON对象" in str(captured.get("system_prompt") or "")
    assert str(captured.get("session_key") or "").startswith("factory_agent:blueprint:")
    assert int(captured.get("timeout_sec") or 0) == 10


def test_build_workpackage_context_contains_protocol_alignment_fields(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    context = agent._build_workpackage_context("创建地址治理工作包")
    assert isinstance(context.get("schema_reference"), dict)
    assert str((context.get("schema_reference") or {}).get("schema_version") or "") == "workpackage_schema.v1"
    assert isinstance(context.get("runtime_constraints"), dict)
    runtime_constraints = context.get("runtime_constraints") or {}
    assert runtime_constraints.get("no_fallback") is True
    assert runtime_constraints.get("no_mock") is True
    assert isinstance(context.get("conversation_facts"), list)
    assert isinstance(context.get("registered_api_catalog_digest"), str)


def test_compact_workpackage_context_for_llm_limits_api_payload(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    context = {
        "architecture_context": {"layers": ["L1"]},
        "schema_reference": {"schema_version": "workpackage_schema.v1"},
        "runtime_constraints": {"no_mock": True},
        "alignment_checklist": ["a", "b"],
        "registered_api_catalog_digest": "abc",
        "registered_api_catalog": [
            {"source_id": "s", "interface_id": f"i{k}", "name": "n", "base_url": "u", "method": "GET"} for k in range(20)
        ],
        "trusted_hub_sources": [{"source_id": "s1"}, {"source_id": "s2"}],
        "conversation_facts": ["x1", "x2", "x3", "x4", "x5"],
        "user_prompt": "p",
    }
    compact = agent._compact_workpackage_context_for_llm(context)
    assert isinstance(compact, dict)
    assert len(compact.get("registered_api_catalog_top") or []) == 12
    assert compact.get("trusted_hub_source_count") == 2
    assert compact.get("conversation_facts") == ["x2", "x3", "x4", "x5"]


def test_converse_returns_blocked_when_llm_fails(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()

    def _raise(_prompt: str):
        raise RuntimeError("llm down")

    monkeypatch.setattr(agent, "_run_requirement_query", _raise)

    result = agent.converse("请生成地址治理 MVP 方案")
    assert result["status"] == "blocked"
    assert result["action"] == "confirm_requirement"
    assert "llm" in str(result.get("reason", "")).lower()


def test_converse_exposes_exception_class_when_llm_error_message_empty(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()

    def _raise(_prompt: str):
        raise TimeoutError()

    monkeypatch.setattr(agent, "_run_general_chat_query", _raise)
    result = agent.converse("请给出数据治理建议")
    assert result["status"] == "blocked"
    assert result["action"] == "general_governance_chat"
    assert "TimeoutError" in str(result.get("error") or "")


def test_converse_returns_structured_summary_when_llm_ok(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    answer = """
{
  "target": "地址标准化与去重",
  "data_sources": ["gaode_api", "baidu_api"],
  "rule_points": ["结构化解析", "冲突评分"],
  "outputs": ["workpackage", "observability_report"]
}
""".strip()
    monkeypatch.setattr(agent, "_run_requirement_query", lambda _prompt: {"status": "ok", "answer": answer})

    result = agent.converse("请生成地址治理 MVP 方案")
    assert result["status"] == "ok"
    assert result["action"] == "confirm_requirement"
    assert result["summary"]["target"] == "地址标准化与去重"
    assert result["summary"]["data_sources"] == ["gaode_api", "baidu_api"]


def test_extract_requirement_summary_coerces_target_from_array(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    summary = agent._extract_requirement_summary(
        '{"target":["地址标准化","地址验真"],"data_sources":["gaode_api"],"rule_points":["结构化解析"],"outputs":["workpackage"]}'
    )
    assert summary["target"] == "地址标准化"


def test_converse_returns_friendly_reply_for_non_governance_topic(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    result = agent.converse("今天天气怎么样")
    assert result["status"] == "ok"
    assert result["action"] == "out_of_scope_chat"
    assert "不太擅长" in str(result.get("message") or "")


def test_converse_returns_natural_chat_for_governance_dialogue(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    monkeypatch.setattr(
        agent,
        "_run_general_chat_query",
        lambda _prompt: {
            "status": "ok",
            "answer": "可以先梳理数据源和质量指标，再定义核验规则。",
            "raw": {"id": "chat-demo", "choices": [{"message": {"content": "可以先梳理数据源和质量指标，再定义核验规则。"}}]},
            "request": {"messages": [{"role": "system", "content": "x"}, {"role": "user", "content": "y"}]},
        },
    )
    result = agent.converse("我们先聊聊数据治理落地步骤")
    assert result["status"] == "ok"
    assert result["action"] == "general_governance_chat"
    assert "数据源" in str(result.get("reply") or "")
    assert isinstance(result.get("llm_request"), dict)


def test_converse_treats_data_volume_constraints_as_governance_topic(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    monkeypatch.setattr(
        agent,
        "_run_general_chat_query",
        lambda _prompt: {
            "status": "ok",
            "answer": "在100条数据范围内，建议先做规则验证和抽样复核。",
            "raw": {"id": "chat-demo-2", "choices": [{"message": {"content": "ok"}}]},
            "request": {"messages": [{"role": "system", "content": "x"}, {"role": "user", "content": "y"}]},
        },
    )
    result = agent.converse("数据量只有不超过100条；其他的你输出建议。")
    assert result["status"] == "ok"
    assert result["action"] == "general_governance_chat"
    assert "100条" in str(result.get("reply") or "")


def test_converse_general_chat_json_answer_is_rendered_as_natural_text(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    monkeypatch.setattr(
        agent,
        "_run_general_chat_query",
        lambda _prompt: {
            "status": "ok",
            "answer": '{"status":"ok","action":"out_of_scope_chat","message":"这个话题我不太擅长。","suggestion":"你可以告诉我数据治理目标。"}',
            "raw": {"id": "chat-json-demo"},
            "request": {"messages": [{"role": "user", "content": "p"}]},
        },
    )
    result = agent.converse("a s d f")
    assert result["status"] == "ok"
    assert result["action"] == "general_governance_chat"
    assert "不太擅长" in str(result.get("reply") or "")
    assert '{"status"' not in str(result.get("reply") or "")


def test_generate_workpackage_retries_llm_until_schema_valid(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    calls = {"n": 0}

    invalid_answer = '{"workpackage":{"name":"addr-governance"}}'
    valid_answer = """
{
  "workpackage": {"name": "addr-governance", "version": "v1.0.0", "objective": "地址治理工作包"},
  "architecture_context": {"factory_architecture": "治理工厂四层架构", "runtime_env": {"python": "3.11", "queue": "sync"}},
  "io_contract": {
    "input_schema": {"type": "object", "properties": {"raw_text": {"type": "string"}}, "required": ["raw_text"]},
    "output_schema": {"type": "object", "properties": {"normalization": {"type": "object"}, "address_validation": {"type": "object"}}, "required": ["normalization", "address_validation"]}
  },
  "api_plan": {
    "registered_apis_used": [{"source_id": "fengtu", "interface_id": "address_standardize"}],
    "missing_apis": [{"name": "poi_risk_lookup", "endpoint": "https://example.com/poi-risk", "reason": "补充高风险POI识别", "requires_key": true}]
  },
  "execution_plan": {"steps": ["解析输入", "地址标准化", "地址验真", "空间图谱构建"]},
  "scripts": [{"name": "fetch_poi_risk.py", "purpose": "拉取POI风险数据", "runtime": "python", "entry": "python scripts/fetch_poi_risk.py"}]
}
""".strip()

    def _fake_query(_prompt: str, _context: dict, _feedback: list[str] | None = None) -> dict:
        calls["n"] += 1
        return {"status": "ok", "answer": invalid_answer if calls["n"] == 1 else valid_answer}

    monkeypatch.setattr(agent, "_run_workpackage_blueprint_query", _fake_query)
    result = agent.converse("创建工作包，目标地址标准化+验真+空间图谱")

    assert result["status"] == "ok"
    assert result["action"] == "generate_workpackage"
    assert int(result.get("llm_retry_count") or 0) >= 1
    assert calls["n"] >= 2
    assert isinstance(result.get("schema_errors"), list)


def test_generate_workpackage_contains_context_io_api_and_scripts(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    answer = """
{
  "workpackage": {"name": "addr-factory-pack", "version": "v2.0.0", "objective": "地址治理工作包"},
  "architecture_context": {"factory_architecture": "治理工厂四层架构", "runtime_env": {"python": "3.11", "queue": "sync"}},
  "io_contract": {
    "input_schema": {"type": "object", "properties": {"raw_text": {"type": "string"}}, "required": ["raw_text"]},
    "output_schema": {"type": "object", "properties": {"normalization": {"type": "object"}, "entity_parsing": {"type": "object"}, "address_validation": {"type": "object"}}, "required": ["normalization", "entity_parsing", "address_validation"]}
  },
  "api_plan": {
    "registered_apis_used": [{"source_id": "fengtu", "interface_id": "address_real_check"}],
    "missing_apis": [{"name": "poi_risk_lookup", "endpoint": "https://example.com/poi-risk", "reason": "补充风险识别", "requires_key": true}]
  },
  "execution_plan": {"steps": ["输入校验", "标准化", "验真", "图谱构建"]},
  "scripts": [
    {"name": "fetch_poi_risk.py", "purpose": "拉取风险POI", "runtime": "python", "entry": "python scripts/fetch_poi_risk.py"},
    {"name": "run_pipeline.py", "purpose": "执行治理流程", "runtime": "python", "entry": "python scripts/run_pipeline.py"}
  ]
}
""".strip()
    monkeypatch.setattr(
        agent,
        "_run_workpackage_blueprint_query",
        lambda _prompt, _context, _feedback=None: {"status": "ok", "answer": answer},
    )
    result = agent.converse("创建工作包：对齐输入输出结构，使用可信API，不足则补充外部API并生成脚本")
    assert result["status"] == "ok"
    bundle_path = str(result.get("bundle_path") or "")
    assert bundle_path

    import json
    from pathlib import Path

    workpackage = json.loads((Path(bundle_path) / "workpackage.json").read_text(encoding="utf-8"))
    assert isinstance(workpackage.get("architecture_context"), dict)
    assert isinstance((workpackage.get("io_contract") or {}).get("input_schema"), dict)
    assert isinstance((workpackage.get("io_contract") or {}).get("output_schema"), dict)
    assert isinstance((workpackage.get("api_plan") or {}).get("registered_apis_used"), list)
    assert isinstance((workpackage.get("api_plan") or {}).get("missing_apis"), list)
    assert len(workpackage.get("scripts") or []) >= 1


def test_generate_workpackage_returns_llm_request_with_context(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    answer = """
{
  "workpackage": {"name": "ctx-pack", "version": "v1.0.0", "objective": "上下文验证"},
  "architecture_context": {"factory_architecture": "四层", "runtime_env": {"python": "3.11"}},
  "io_contract": {"input_schema": {"type": "object"}, "output_schema": {"type": "object"}},
  "api_plan": {"registered_apis_used": [{"source_id": "fengtu", "interface_id": "address_standardize"}], "missing_apis": []},
  "execution_plan": {"steps": ["a"]},
  "scripts": [{"name": "run_pipeline.py", "entry": "python scripts/run_pipeline.py"}]
}
""".strip()
    monkeypatch.setattr(
        agent,
        "_run_workpackage_blueprint_query",
        lambda _prompt, _context, _feedback=None: {
            "status": "ok",
            "answer": answer,
            "request": {
                "messages": [
                    {"role": "system", "content": "sys"},
                    {"role": "user", "content": '{"architecture_context":{},"registered_api_catalog":[]}'},
                ]
            },
            "raw": {"id": "resp_1"},
        },
    )

    result = agent.converse("创建工作包，先对齐架构上下文、I/O、已注册API")
    assert result["status"] == "ok"
    assert isinstance(result.get("llm_request"), dict)
    user_messages = [x for x in (result.get("llm_request", {}).get("messages") or []) if x.get("role") == "user"]
    assert user_messages
    user_content = str(user_messages[-1].get("content") or "")
    assert "architecture_context" in user_content
    assert "registered_api_catalog" in user_content


def test_generate_workpackage_autofill_missing_api_and_scripts_when_capability_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("WORKPACKAGE_BLUEPRINT_MAX_ROUNDS", "1")
    agent = FactoryAgent()
    monkeypatch.setattr(agent, "_run_workpackage_blueprint_query", lambda *_args, **_kwargs: {"status": "ok", "answer": '{"workpackage":{"name":"cap-gap"}}'})
    monkeypatch.setattr(
        agent,
        "_load_registered_api_catalog",
        lambda: [{"source_id": "fengtu", "interface_id": "address_standardize", "name": "地址标准化"}],
    )

    result = agent.converse("创建工作包：地址标准化、地址验真、空间实体拆分、空间图谱输出")
    assert result["status"] == "ok"
    blueprint = result.get("workpackage_blueprint") or {}
    missing = ((blueprint.get("api_plan") or {}).get("missing_apis") or [])
    assert isinstance(missing, list)
    assert len(missing) >= 1
    assert any(bool(item.get("requires_key")) for item in missing if isinstance(item, dict))
    scripts = blueprint.get("scripts") or []
    assert any("fetch_" in str(item.get("name") or "") for item in scripts if isinstance(item, dict))
    bundle_path = str(result.get("bundle_path") or "")
    assert bundle_path
    from pathlib import Path
    env_example = Path(bundle_path) / "config" / "provider_keys.env.example"
    assert env_example.exists()


def test_generate_workpackage_returns_schema_fix_rounds_and_generation_trace(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("WORKPACKAGE_BLUEPRINT_MAX_ROUNDS", "2")
    agent = FactoryAgent()
    calls = {"n": 0}
    invalid = '{"workpackage":{"name":"ctx-e2e"}}'
    valid = """
{
  "workpackage": {"name": "ctx-e2e", "version": "v1.0.0", "objective": "地址治理"},
  "architecture_context": {"factory_architecture": {"layers": ["a"]}, "runtime_env": {"python": "3.11"}},
  "io_contract": {"input_schema": {"type": "object"}, "output_schema": {"type": "object"}},
  "api_plan": {"registered_apis_used": [{"source_id": "fengtu", "interface_id": "geocode"}], "missing_apis": []},
  "execution_plan": {"steps": ["s1"]},
  "scripts": [{"name": "run_pipeline.py", "entry": "python scripts/run_pipeline.py"}]
}
""".strip()

    def _fake_query(_prompt: str, _context: dict, _feedback=None):
        calls["n"] += 1
        answer = invalid if calls["n"] == 1 else valid
        return {"status": "ok", "answer": answer}

    monkeypatch.setattr(agent, "_run_workpackage_blueprint_query", _fake_query)
    result = agent.converse("请生成地址治理工作包")
    assert result["status"] == "ok"
    fix_rounds = result.get("schema_fix_rounds")
    assert isinstance(fix_rounds, list)
    assert len(fix_rounds) >= 1
    assert isinstance(result.get("generation_trace"), dict)
    from pathlib import Path
    import json

    bundle_path = Path(str(result.get("bundle_path") or ""))
    payload = json.loads((bundle_path / "workpackage.json").read_text(encoding="utf-8"))
    assert payload.get("generation_trace") is None
    assert payload.get("schema_version") == "workpackage_schema.v1"


def test_generate_workpackage_blocks_when_all_llm_calls_fail(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("WORKPACKAGE_BLUEPRINT_MAX_ROUNDS", "2")
    agent = FactoryAgent()

    def _raise_llm_401(*_args, **_kwargs):
        raise RuntimeError("Error: Error code: 401 - {'error': 'Invalid API key'}")

    monkeypatch.setattr(agent, "_run_workpackage_blueprint_query", _raise_llm_401)
    result = agent.converse("创建地址治理工作包并生成脚本")
    assert result.get("status") == "blocked"
    assert result.get("action") == "generate_workpackage"
    assert result.get("requires_user_confirmation") is True
    assert "401" in str(result.get("error") or "")


def test_generate_workpackage_ignores_llm_script_content_and_uses_opencode_builder(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    answer = """
{
  "workpackage": {"name": "builder-pack", "version": "v1.0.0", "objective": "builder test"},
  "architecture_context": {"factory_architecture": {"layers": ["a"]}, "runtime_env": {"python": "3.11"}},
  "io_contract": {"input_schema": {"type": "object"}, "output_schema": {"type": "object"}},
  "api_plan": {"registered_apis_used": [{"source_id": "fengtu", "interface_id": "geocode"}], "missing_apis": []},
  "execution_plan": {"steps": ["s1"]},
  "scripts": [{
    "name": "run_pipeline.py",
    "purpose": "run",
    "runtime": "python",
    "entry": "python scripts/run_pipeline.py",
    "content": "print('llm_script_content_should_not_be_used')"
  }]
}
""".strip()
    monkeypatch.setattr(agent, "_run_workpackage_blueprint_query", lambda *_a, **_k: {"status": "ok", "answer": answer})
    result = agent.converse("创建工作包并生成脚本")
    assert result["status"] == "ok"
    from pathlib import Path
    bundle_path = Path(str(result.get("bundle_path") or ""))
    script_text = (bundle_path / "scripts" / "run_pipeline.py").read_text(encoding="utf-8")
    assert "llm_script_content_should_not_be_used" not in script_text
    assert "generated_by = \"opencode_agent\"" in script_text


def test_generate_workpackage_missing_api_is_proposal_only_without_hub_upsert(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    answer = """
{
  "workpackage": {"name": "proposal-pack", "version": "v1.0.0", "objective": "proposal"},
  "architecture_context": {"factory_architecture": {"layers": ["a"]}, "runtime_env": {"python": "3.11"}},
  "io_contract": {"input_schema": {"type": "object"}, "output_schema": {"type": "object"}},
  "api_plan": {
    "registered_apis_used": [],
    "missing_apis": [{"name":"ext-a","endpoint":"https://ext-a.example.com","reason":"need","requires_key":true}]
  },
  "execution_plan": {"steps": ["s1"]},
  "scripts": [{"name":"run_pipeline.py","entry":"python scripts/run_pipeline.py"}]
}
""".strip()
    monkeypatch.setattr(agent, "_run_workpackage_blueprint_query", lambda *_a, **_k: {"status": "ok", "answer": answer})
    calls = {"n": 0}

    def _forbidden_upsert(*_args, **_kwargs):
        calls["n"] += 1
        raise AssertionError("generate phase should not upsert trust hub capability")

    monkeypatch.setattr(agent._trust_hub, "upsert_capability", _forbidden_upsert)
    result = agent.converse("创建工作包，需要补齐缺失API")
    assert result["status"] == "ok"
    assert calls["n"] == 0
    blueprint = result.get("workpackage_blueprint") or {}
    assert isinstance(((blueprint.get("api_plan") or {}).get("missing_apis")), list)


def test_generate_entrypoint_py_uses_subprocess_instead_of_exec(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    script = agent._generate_entrypoint_py()
    assert "exec(" not in script
    assert "subprocess.run" in script


def test_generate_workpackage_delegates_bundle_build_to_opencode_builder(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    called = {"n": 0, "bundle_dir": ""}

    class _FakeBuilder:
        def build_bundle(self, *, bundle_dir, blueprint, sources):
            called["n"] += 1
            called["bundle_dir"] = str(bundle_dir)

    monkeypatch.setattr(agent, "_workpackage_builder", _FakeBuilder())
    answer = """
{
  "workpackage": {"name": "delegate-pack", "version": "v1.0.0", "objective": "delegate"},
  "architecture_context": {"factory_architecture": {"layers": ["a"]}, "runtime_env": {"python": "3.11"}},
  "io_contract": {"input_schema": {"type": "object"}, "output_schema": {"type": "object"}},
  "api_plan": {"registered_apis_used": [{"source_id": "fengtu", "interface_id": "geocode"}], "missing_apis": []},
  "execution_plan": {"steps": ["s1"]},
  "scripts": [{"name": "run_pipeline.py", "entry": "python scripts/run_pipeline.py"}]
}
""".strip()
    monkeypatch.setattr(agent, "_run_workpackage_blueprint_query", lambda *_a, **_k: {"status": "ok", "answer": answer})
    result = agent.converse("创建工作包")
    assert result["status"] == "ok"
    assert called["n"] == 1
    assert "delegate-pack-v1.0.0" in called["bundle_dir"]
