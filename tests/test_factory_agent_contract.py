from packages.factory_agent.agent import FactoryAgent


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
