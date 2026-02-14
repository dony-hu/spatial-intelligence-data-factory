from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.process_compiler import ProcessCompiler
from tools.process_tools.design_process_tool import DesignProcessTool
from tools.process_tools.modify_process_tool import ModifyProcessTool


class InMemoryProcessRuntimeStore:
    def __init__(self) -> None:
        self._drafts: Dict[str, Dict[str, Any]] = {}
        self._process_defs: Dict[str, Dict[str, Any]] = {}

    def upsert_process_draft(self, **kwargs: Any) -> Dict[str, Any]:
        draft_id = str(kwargs.get("draft_id") or f"draft_{uuid.uuid4().hex[:10]}")
        self._drafts[draft_id] = dict(kwargs)
        return {
            "draft_id": draft_id,
            "updated_at": datetime.now().isoformat(),
            "status": kwargs.get("status", "editable"),
        }

    def find_process_definition(self, code: str) -> Optional[Dict[str, Any]]:
        return self._process_defs.get(str(code or "").upper())

    def ensure_process_definition(self, code: str, name: str, domain: str) -> Dict[str, Any]:
        final_code = str(code or "").upper()
        hit = self._process_defs.get(final_code)
        if hit:
            return hit
        item = {
            "id": f"procdef_{uuid.uuid4().hex[:12]}",
            "code": final_code,
            "name": name,
            "domain": domain,
        }
        self._process_defs[final_code] = item
        return item


class ProcessExpertLLMBridge:
    def generate_plan(self, requirement: str) -> Dict[str, Any]:
        raise NotImplementedError

    def suggest_change_request(self, round_index: int, audit: Dict[str, Any], last_result: Dict[str, Any]) -> str:
        raise NotImplementedError

    def pop_trace_events(self) -> List[Dict[str, Any]]:
        return []

    def recommend_trusted_sources(self, trusted_sources_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"recommendations": []}


@dataclass
class BootstrapRound:
    round_index: int
    stage: str
    result: Dict[str, Any]
    audit: Dict[str, Any]
    score: float
    round_dir: Optional[Path] = None


class ProcessExpertBootstrapRunner:
    def __init__(
        self,
        llm_bridge: ProcessExpertLLMBridge,
        cases_file: Path,
        output_dir: Path,
        max_rounds: int = 3,
        min_rounds: int = 1,
        score_threshold: float = 0.82,
        trusted_sources_config_path: Optional[Path] = None,
    ) -> None:
        self.llm_bridge = llm_bridge
        self.cases_file = cases_file
        self.output_dir = output_dir
        self.max_rounds = max_rounds
        self.min_rounds = max(1, min_rounds)
        self.score_threshold = score_threshold
        self.trusted_sources_config_path = trusted_sources_config_path
        self.trusted_sources_config = self._load_trusted_sources_config(trusted_sources_config_path)

        self.runtime_store = InMemoryProcessRuntimeStore()
        self.compiler = ProcessCompiler()

        self.design_tool = DesignProcessTool(
            runtime_store=self.runtime_store,
            process_compiler=self.compiler,
            llm_service=self.llm_bridge,
        )
        self.modify_tool = ModifyProcessTool(
            runtime_store=self.runtime_store,
            process_compiler=self.compiler,
            llm_service=self.llm_bridge,
        )

    def run(self, process_code: str = "PROC_TOOLPACK_BOOTSTRAP") -> Dict[str, Any]:
        cases_data = json.loads(self.cases_file.read_text(encoding="utf-8"))
        cases = list(cases_data.get("cases") or [])
        summary = self._summarize_cases(cases)
        story_rule = self._extract_story_rule(cases)
        capability_matrix = self._build_trusted_interface_capability_matrix(self.trusted_sources_config)
        run_id = f"bootstrap_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run_dir = self.output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        rounds: List[BootstrapRound] = []
        llm_trace: List[Dict[str, Any]] = []
        requirement = self._build_requirement_from_cases(summary, capability_matrix)
        stop_reason = "max_rounds_reached"

        first = self.design_tool.execute(
            {
                "requirement": requirement,
                "process_code": process_code,
                "process_name": "工具包生成工艺",
                "domain": "verification",
            },
            session_id=f"{run_id}_r1",
        )
        self.runtime_store.ensure_process_definition(
            code=str(first.get("process_code") or process_code),
            name=str(first.get("process_name") or "工具包生成工艺"),
            domain=str(first.get("domain") or "verification"),
        )
        first_audit = self._audit_result(first, summary, story_rule, self.trusted_sources_config)
        first_audit["trusted_interface_capabilities"] = capability_matrix.get("capability_index") or {}
        first_audit["suggested_interface_plan"] = self._build_interface_strategy_for_gaps(
            audit_gaps=list(first_audit.get("audit_gaps") or []),
            capability_matrix=capability_matrix,
        )
        first_audit["evidence_checklist_template"] = self._build_evidence_checklist_template(
            suggested_interface_plan=first_audit.get("suggested_interface_plan") or {},
            audit_gaps=list(first_audit.get("audit_gaps") or []),
        )
        rounds.append(BootstrapRound(1, "design", first, first_audit, first_audit["score"]))
        round1_events = self.llm_bridge.pop_trace_events()
        llm_trace.extend(round1_events)
        rounds[-1].round_dir = self._persist_round(run_dir, rounds[-1], llm_events=round1_events)

        current = first
        for idx in range(2, self.max_rounds + 1):
            if (idx - 1) >= self.min_rounds and rounds[-1].score >= self.score_threshold:
                stop_reason = "threshold_met"
                break
            change_request = self.llm_bridge.suggest_change_request(
                round_index=idx,
                audit=rounds[-1].audit,
                last_result=current,
            )
            modified = self.modify_tool.execute(
                {
                    "process_code": str(current.get("process_code") or process_code),
                    "change_request": change_request,
                    "goal": "提升工艺文档质量与工具脚本完备度",
                },
                session_id=f"{run_id}_r{idx}",
            )
            mod_audit = self._audit_result(modified, summary, story_rule, self.trusted_sources_config)
            mod_audit["trusted_interface_capabilities"] = capability_matrix.get("capability_index") or {}
            mod_audit["suggested_interface_plan"] = self._build_interface_strategy_for_gaps(
                audit_gaps=list(mod_audit.get("audit_gaps") or []),
                capability_matrix=capability_matrix,
            )
            mod_audit["evidence_checklist_template"] = self._build_evidence_checklist_template(
                suggested_interface_plan=mod_audit.get("suggested_interface_plan") or {},
                audit_gaps=list(mod_audit.get("audit_gaps") or []),
            )
            rounds.append(BootstrapRound(idx, "modify", modified, mod_audit, mod_audit["score"]))
            round_events = self.llm_bridge.pop_trace_events()
            llm_trace.extend(round_events)
            rounds[-1].round_dir = self._persist_round(run_dir, rounds[-1], llm_events=round_events)
            current = modified

        if stop_reason != "threshold_met":
            stop_reason = "max_rounds_reached" if len(rounds) >= self.max_rounds else "early_stop"

        next_iteration_plan: Optional[Dict[str, Any]] = None
        if rounds and rounds[-1].score < self.score_threshold:
            try:
                next_change_request = self.llm_bridge.suggest_change_request(
                    round_index=len(rounds) + 1,
                    audit=rounds[-1].audit,
                    last_result=current,
                )
                extra_events = self.llm_bridge.pop_trace_events()
                llm_trace.extend(extra_events)
            except Exception:
                next_change_request = "根据失败项补强真实性双源确认、标准化补齐街道、分词图谱链与明确结论"

            rerun_command = (
                "python scripts/run_process_expert_bootstrap.py "
                f"--cases-file {self.cases_file.relative_to(Path(__file__).resolve().parent.parent)} "
                f"--output-dir {self.output_dir.relative_to(Path(__file__).resolve().parent.parent)} "
                f"--max-rounds {max(self.max_rounds + 1, 2)} --min-rounds {max(self.min_rounds, 2)} "
                f"--score-threshold {self.score_threshold}"
            )
            next_iteration_plan = {
                "needed": True,
                "reason": "当前审计未达阈值，需继续迭代",
                "suggested_change_request": next_change_request,
                "suggested_rerun_command": rerun_command,
            }
            (run_dir / "next_iteration_plan.json").write_text(
                json.dumps(next_iteration_plan, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        best = max(rounds, key=lambda r: r.score)
        final_payload = {
            "status": "ok",
            "run_id": run_id,
            "cases_file": str(self.cases_file),
            "rounds": [
                {
                    "round": r.round_index,
                    "stage": r.stage,
                    "score": r.score,
                    "audit": r.audit,
                    "process_code": r.result.get("process_code"),
                    "draft_id": r.result.get("draft_id"),
                }
                for r in rounds
            ],
            "best_round": {
                "round": best.round_index,
                "score": best.score,
                "draft_id": best.result.get("draft_id"),
                "process_code": best.result.get("process_code"),
            },
            "llm_interaction_count": len(llm_trace),
            "min_rounds": self.min_rounds,
            "max_rounds": self.max_rounds,
            "story_rule_enabled": bool(story_rule.get("enabled")),
            "meets_threshold": best.score >= self.score_threshold,
            "trusted_interface_capability_count": int(capability_matrix.get("interface_count") or 0),
            "stop_reason": stop_reason,
            "next_iteration_plan": next_iteration_plan,
        }
        (run_dir / "final_summary.json").write_text(json.dumps(final_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (run_dir / "llm_interactions.json").write_text(json.dumps(llm_trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (run_dir / "llm_interactions.jsonl").write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in llm_trace) + ("\n" if llm_trace else ""),
            encoding="utf-8",
        )
        self._persist_trusted_source_recommendations(run_dir, summary)
        (run_dir / "trusted_interface_capabilities.json").write_text(
            json.dumps(capability_matrix, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self._persist_workpackage_process_artifact(run_dir, rounds, case_summary=summary)
        return final_payload

    @staticmethod
    def _load_trusted_sources_config(path: Optional[Path]) -> Dict[str, Any]:
        if not path:
            return {"trusted_sources": [], "llm_recommendation": {"enabled": False}}
        if not path.exists():
            return {"trusted_sources": [], "llm_recommendation": {"enabled": False}, "missing_config": str(path)}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"trusted_sources": [], "llm_recommendation": {"enabled": False}, "invalid_config": str(path)}
            return data
        except Exception as exc:
            return {
                "trusted_sources": [],
                "llm_recommendation": {"enabled": False},
                "invalid_config": str(path),
                "error": str(exc),
            }

    def _persist_trusted_source_recommendations(self, run_dir: Path, case_summary: Dict[str, Any]) -> None:
        llm_cfg = self.trusted_sources_config.get("llm_recommendation") or {}
        if not bool(llm_cfg.get("enabled", False)):
            return
        payload = self.llm_bridge.recommend_trusted_sources(
            trusted_sources_config=self.trusted_sources_config,
            context={
                "case_summary": case_summary,
                "cases_file": str(self.cases_file),
            },
        )
        (run_dir / "trusted_source_recommendations.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _summarize_cases(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        priorities: Dict[str, int] = {}
        categories: Dict[str, int] = {}
        expected_statuses: Dict[str, int] = {}
        for case in cases:
            p = str(case.get("priority") or "P2")
            priorities[p] = priorities.get(p, 0) + 1
            cat = str(case.get("category") or "unknown")
            categories[cat] = categories.get(cat, 0) + 1
            expected = case.get("expected") or {}
            if isinstance(expected, dict):
                status = str(expected.get("verification_status") or "").strip()
                if status:
                    expected_statuses[status] = expected_statuses.get(status, 0) + 1
        return {
            "total": len(cases),
            "priorities": priorities,
            "categories": categories,
            "expected_statuses": expected_statuses,
        }

    @staticmethod
    def _build_requirement_from_cases(summary: Dict[str, Any], capability_matrix: Optional[Dict[str, Any]] = None) -> str:
        capability_matrix = capability_matrix or {}
        capability_index = capability_matrix.get("capability_index") or {}
        return (
            "请设计工具包生成工艺，要求支持地图API采样、LLM归并、审计回放、迭代改进。\n"
            "请在工艺中显式体现可信数据源能力编排、证据采集、结论输出与未决风险。\n"
            f"用例总量: {summary.get('total')}\n"
            f"优先级分布: {json.dumps(summary.get('priorities') or {}, ensure_ascii=False)}\n"
            f"类别分布: {json.dumps(summary.get('categories') or {}, ensure_ascii=False)}\n"
            f"期望核实状态分布: {json.dumps(summary.get('expected_statuses') or {}, ensure_ascii=False)}\n"
            f"可信接口能力索引: {json.dumps(capability_index, ensure_ascii=False)}\n"
            "工艺输出必须包含: 证据清单、结论段、未决风险段。\n"
        )

    @staticmethod
    def _infer_interface_capability_tags(interface_id: str, interface_name: str) -> List[str]:
        text = f"{interface_id} {interface_name}".lower()
        tags: List[str] = []
        if any(k in text for k in ["real", "真实性", "auth"]):
            tags.extend(["真实性校验", "结论判定"])
        if any(k in text for k in ["std", "标准化"]):
            tags.extend(["地址标准化", "结构化拆解"])
        if any(k in text for k in ["aoi", "keyword", "聚合"]):
            tags.extend(["AOI提取", "地标聚合"])
        if any(k in text for k in ["resolve", "五级", "区划"]):
            tags.extend(["五级解析", "行政区划解析"])
        if any(k in text for k in ["level", "judge", "级别"]):
            tags.extend(["地址完备度评估", "冲突检测"])
        if any(k in text for k in ["type", "类型"]):
            tags.extend(["地址类型识别", "画像分类"])
        if any(k in text for k in ["geo", "geocode", "坐标", "place"]):
            tags.extend(["坐标解析", "位置检索"])
        seen = set()
        ordered: List[str] = []
        for tag in tags:
            if tag not in seen:
                ordered.append(tag)
                seen.add(tag)
        return ordered or ["地址核实"]

    @classmethod
    def _build_trusted_interface_capability_matrix(cls, trusted_sources_config: Dict[str, Any]) -> Dict[str, Any]:
        sources = list(trusted_sources_config.get("trusted_sources") or [])
        rows: List[Dict[str, Any]] = []
        capability_index: Dict[str, List[Dict[str, Any]]] = {}
        for src in sources:
            if not isinstance(src, dict):
                continue
            source_id = str(src.get("source_id") or "")
            source_name = str(src.get("name") or "")
            provider = str(src.get("provider") or "")
            interfaces = src.get("trusted_interfaces") or []
            normalized_interfaces: List[Dict[str, Any]] = []
            if isinstance(interfaces, list) and interfaces:
                for itf in interfaces:
                    if not isinstance(itf, dict):
                        continue
                    interface_id = str(itf.get("interface_id") or "default")
                    interface_name = str(itf.get("name") or interface_id)
                    tags = cls._infer_interface_capability_tags(interface_id, interface_name)
                    item = {
                        "source_id": source_id,
                        "source_name": source_name,
                        "provider": provider,
                        "interface_id": interface_id,
                        "interface_name": interface_name,
                        "method": str(itf.get("method") or "GET").upper(),
                        "base_url": str(itf.get("base_url") or ""),
                        "ak_in": str(itf.get("ak_in") or "header"),
                        "capability_tags": tags,
                    }
                    normalized_interfaces.append(item)
                    for tag in tags:
                        capability_index.setdefault(tag, []).append(
                            {
                                "source_id": source_id,
                                "interface_id": interface_id,
                                "interface_name": interface_name,
                            }
                        )
            else:
                req = src.get("request") or {}
                interface_id = "default"
                interface_name = source_name or interface_id
                tags = cls._infer_interface_capability_tags(interface_id=source_id, interface_name=interface_name)
                item = {
                    "source_id": source_id,
                    "source_name": source_name,
                    "provider": provider,
                    "interface_id": interface_id,
                    "interface_name": interface_name,
                    "method": str(req.get("method") or "GET").upper(),
                    "base_url": str(src.get("base_url") or ""),
                    "ak_in": "header",
                    "capability_tags": tags,
                }
                normalized_interfaces.append(item)
                for tag in tags:
                    capability_index.setdefault(tag, []).append(
                        {
                            "source_id": source_id,
                            "interface_id": interface_id,
                            "interface_name": interface_name,
                        }
                    )

            rows.append(
                {
                    "source_id": source_id,
                    "source_name": source_name,
                    "provider": provider,
                    "interfaces": normalized_interfaces,
                }
            )

        interface_count = sum(len(x.get("interfaces") or []) for x in rows)
        return {
            "source_count": len(rows),
            "interface_count": interface_count,
            "sources": rows,
            "capability_index": capability_index,
        }

    @staticmethod
    def _build_audit_gaps(failed_checks: List[str]) -> List[Dict[str, Any]]:
        gap_templates: Dict[str, Dict[str, Any]] = {
            "story_authenticity_two_trusted_sources": {
                "priority": "P0",
                "goal": "至少两个可信源交叉验证",
                "recommended_capabilities": ["真实性校验", "地址标准化", "AOI提取"],
                "expected_evidence": ["跨源比对结果", "冲突说明", "最终判定"],
            },
            "story_clear_conclusion": {
                "priority": "P0",
                "goal": "输出明确真实性结论",
                "recommended_capabilities": ["真实性校验", "结论判定"],
                "expected_evidence": ["结论段", "判定依据"],
            },
            "story_token_graph_chain_present": {
                "priority": "P1",
                "goal": "补全分词-图谱-链路过程",
                "recommended_capabilities": ["地址标准化", "五级解析"],
                "expected_evidence": ["分词结果", "链路说明"],
            },
            "contains_iteration_keywords": {
                "priority": "P1",
                "goal": "补齐迭代与审计回放描述",
                "recommended_capabilities": ["审计回放"],
                "expected_evidence": ["迭代策略", "回放步骤"],
            },
            "has_tool_scripts": {
                "priority": "P1",
                "goal": "补齐可执行脚本产物",
                "recommended_capabilities": ["工具编译"],
                "expected_evidence": ["脚本列表", "脚本说明"],
            },
            "doc_length_ok": {
                "priority": "P2",
                "goal": "补全工艺说明细节",
                "recommended_capabilities": ["工艺文档"],
                "expected_evidence": ["输入输出说明", "异常分支说明"],
            },
        }

        gaps: List[Dict[str, Any]] = []
        for check in failed_checks:
            tpl = gap_templates.get(check) or {
                "priority": "P2",
                "goal": f"修复审计失败项: {check}",
                "recommended_capabilities": ["通用修复"],
                "expected_evidence": ["修复说明"],
            }
            gaps.append(
                {
                    "check": check,
                    "priority": tpl["priority"],
                    "goal": tpl["goal"],
                    "recommended_capabilities": list(tpl["recommended_capabilities"]),
                    "expected_evidence": list(tpl["expected_evidence"]),
                }
            )
        return gaps

    @staticmethod
    def _build_interface_strategy_for_gaps(
        audit_gaps: List[Dict[str, Any]],
        capability_matrix: Dict[str, Any],
    ) -> Dict[str, Any]:
        capability_index = dict(capability_matrix.get("capability_index") or {})
        selected: List[Dict[str, Any]] = []
        seen = set()
        for gap in audit_gaps:
            required_caps = list(gap.get("recommended_capabilities") or [])
            for cap in required_caps:
                candidates = list(capability_index.get(cap) or [])
                for cand in candidates[:2]:
                    key = (str(cand.get("source_id")), str(cand.get("interface_id")))
                    if key in seen:
                        continue
                    selected.append(
                        {
                            "capability": cap,
                            "source_id": cand.get("source_id"),
                            "interface_id": cand.get("interface_id"),
                            "interface_name": cand.get("interface_name"),
                            "target_gap": gap.get("check"),
                        }
                    )
                    seen.add(key)

        return {
            "selected_interface_count": len(selected),
            "selected_interfaces": selected,
        }

    @staticmethod
    def _build_evidence_checklist_template(
        suggested_interface_plan: Dict[str, Any],
        audit_gaps: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        selected = list(suggested_interface_plan.get("selected_interfaces") or [])
        selected_by_gap: Dict[str, List[str]] = {}
        for item in selected:
            gap = str(item.get("target_gap") or "")
            line = f"{item.get('source_id')}/{item.get('interface_id')}"
            selected_by_gap.setdefault(gap, []).append(line)

        checklist: List[Dict[str, Any]] = []
        for gap in audit_gaps:
            check = str(gap.get("check") or "")
            checklist.append(
                {
                    "check": check,
                    "goal": gap.get("goal"),
                    "expected_evidence": list(gap.get("expected_evidence") or []),
                    "recommended_interfaces": selected_by_gap.get(check, []),
                    "required_output_sections": ["证据清单", "结论段", "未决风险段"],
                }
            )
        return checklist

    @staticmethod
    def _extract_story_rule(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        target_address = "广东省深圳市南山区前海顺丰总部大厦"
        for case in cases:
            input_payload = case.get("input") or {}
            raw = str(input_payload.get("raw") or "").strip()
            if raw != target_address:
                continue
            expected = case.get("expected") or {}
            return {
                "enabled": True,
                "target_address": target_address,
                "min_trusted_source_count": int(expected.get("min_trusted_source_count") or 2),
                "required_standard_components": list(expected.get("required_standard_components") or ["province", "city", "district", "street", "poi"]),
                "token_graph_chain_required": bool(expected.get("token_graph_chain_required", True)),
                "clear_conclusion_required": bool(expected.get("audit_must_have_clear_conclusion", True)),
            }
        return {"enabled": False}

    @staticmethod
    def _audit_result(
        result: Dict[str, Any],
        case_summary: Dict[str, Any],
        story_rule: Dict[str, Any],
        trusted_sources_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        compilation = result.get("compilation") or {}
        process_doc = str(result.get("process_doc_markdown") or "")
        tool_scripts = compilation.get("tool_scripts") or {}
        steps = (result.get("plan") or {}).get("steps") or []
        script_blob = "\n".join(str(v or "") for v in (tool_scripts.values() if isinstance(tool_scripts, dict) else []))
        combined = f"{process_doc}\n{script_blob}"

        checks = {
            "status_ok": result.get("status") == "ok",
            "compile_success": bool(compilation.get("success")),
            "has_process_spec": bool(compilation.get("process_spec")),
            "has_tool_scripts": isinstance(tool_scripts, dict) and len(tool_scripts) >= 2,
            "doc_length_ok": len(process_doc) >= 200,
            "contains_iteration_keywords": any(k in process_doc for k in ["迭代", "审计", "质量", "回放"]),
            "plan_steps_ok": len(steps) >= 3,
        }

        if story_rule.get("enabled"):
            lowered = combined.lower()
            trusted_sources = list(trusted_sources_config.get("trusted_sources") or [])
            hit_source_ids = set()
            hit_interface_ids = set()
            for item in trusted_sources:
                if not isinstance(item, dict):
                    continue
                source_id = str(item.get("source_id") or "").strip()
                aliases = [str(x).strip() for x in (item.get("aliases") or []) if str(x).strip()]
                name = str(item.get("name") or "").strip()
                provider = str(item.get("provider") or "").strip()
                candidates = [source_id, name, provider] + aliases
                if any(c and c.lower() in lowered for c in candidates):
                    if source_id:
                        hit_source_ids.add(source_id)

                for itf in list(item.get("trusted_interfaces") or []):
                    if not isinstance(itf, dict):
                        continue
                    interface_id = str(itf.get("interface_id") or "").strip()
                    interface_name = str(itf.get("name") or "").strip()
                    interface_candidates = [interface_id, interface_name]
                    if any(c and c.lower() in lowered for c in interface_candidates):
                        if interface_id:
                            hit_interface_ids.add(interface_id)

            required_components = [str(x).lower() for x in list(story_rule.get("required_standard_components") or [])]
            component_hits = 0
            for comp in required_components:
                if comp and comp in lowered:
                    component_hits += 1
            has_street = ("street" in lowered) or ("街道" in combined)

            graph_chain_hits = ["分词", "拆解", "图谱", "链", "graph", "token"]
            graph_hit_count = sum(1 for k in graph_chain_hits if k.lower() in lowered)

            has_conclusion = any(k in combined for k in ["结论", "明确", "真实性确认", "VERIFIED_EXISTS", "真实存在"]) 

            auth_confirmation = any(k in combined for k in ["真实性确认", "真实性结论", "真实存在", "VERIFIED_EXISTS", "地址真实"])
            standardization_confirmation = has_street and any(
                k in combined for k in ["标准化补齐", "标准化结果", "standardization", "街道补齐", "补齐结果"]
            )
            graph_chain_confirmation = any(
                k in combined for k in ["分词拆解", "图谱链", "图谱链路", "token graph", "graph chain"]
            ) and graph_hit_count >= 3

            checks["story_authenticity_two_trusted_sources"] = (
                len(hit_interface_ids) >= int(story_rule.get("min_trusted_source_count") or 2)
            ) and auth_confirmation
            checks["story_standardized_completion_with_street"] = (
                (component_hits >= max(3, len(required_components) // 2)) and has_street and standardization_confirmation
            )
            checks["story_token_graph_chain_present"] = (
                graph_chain_confirmation if bool(story_rule.get("token_graph_chain_required")) else True
            )
            checks["story_clear_conclusion"] = has_conclusion if bool(story_rule.get("clear_conclusion_required")) else True

            story_requirement_confirmations = [
                {
                    "requirement_id": "R1_authenticity_two_trusted_interfaces",
                    "description": "真实性确认必须来自至少两个可信接口",
                    "passed": bool(checks["story_authenticity_two_trusted_sources"]),
                    "conclusion": "已明确" if bool(checks["story_authenticity_two_trusted_sources"]) else "未明确",
                    "evidence": {
                        "hit_interface_ids": sorted(list(hit_interface_ids)),
                        "auth_confirmation": auth_confirmation,
                    },
                },
                {
                    "requirement_id": "R2_standardization_with_street",
                    "description": "标准化补齐结果必须包含街道",
                    "passed": bool(checks["story_standardized_completion_with_street"]),
                    "conclusion": "已明确" if bool(checks["story_standardized_completion_with_street"]) else "未明确",
                    "evidence": {
                        "component_hits": component_hits,
                        "has_street": has_street,
                        "standardization_confirmation": standardization_confirmation,
                    },
                },
                {
                    "requirement_id": "R3_tokenization_graph_chain",
                    "description": "必须包含地址标准化分词拆解并形成图谱链",
                    "passed": bool(checks["story_token_graph_chain_present"]),
                    "conclusion": "已明确" if bool(checks["story_token_graph_chain_present"]) else "未明确",
                    "evidence": {
                        "graph_hit_count": graph_hit_count,
                        "graph_chain_confirmation": graph_chain_confirmation,
                    },
                },
            ]
        else:
            story_requirement_confirmations = []

        score = sum(1.0 for ok in checks.values() if ok) / float(len(checks))
        failed = [name for name, ok in checks.items() if not ok]
        audit_gaps = ProcessExpertBootstrapRunner._build_audit_gaps(failed)
        failed_check_analysis = ProcessExpertBootstrapRunner._build_failed_check_analysis(
            failed_checks=failed,
            checks=checks,
            story_requirement_confirmations=story_requirement_confirmations,
        )
        return {
            "score": score,
            "checks": checks,
            "failed_checks": failed,
            "failed_check_analysis": failed_check_analysis,
            "audit_gaps": audit_gaps,
            "story_requirement_confirmations": story_requirement_confirmations,
            "case_total": case_summary.get("total", 0),
            "tool_count": len(tool_scripts) if isinstance(tool_scripts, dict) else 0,
            "story_rule_enabled": bool(story_rule.get("enabled")),
            "trusted_source_config_count": len(list(trusted_sources_config.get("trusted_sources") or [])),
        }

    @staticmethod
    def _build_failed_check_analysis(
        failed_checks: List[str],
        checks: Dict[str, Any],
        story_requirement_confirmations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        reason_templates: Dict[str, str] = {
            "story_authenticity_two_trusted_sources": "未满足至少两个可信接口交叉确认，或缺少真实性明确结论。",
            "story_standardized_completion_with_street": "标准化补齐证据不足，街道字段未明确补齐。",
            "story_token_graph_chain_present": "分词拆解与图谱链路描述不足，未形成完整链条结论。",
            "story_clear_conclusion": "缺少明确结论段，无法形成可审计判定。",
            "contains_iteration_keywords": "文档缺少迭代/审计/回放相关过程描述。",
            "has_tool_scripts": "可执行脚本数量或内容不足，无法支撑流程落地。",
            "compile_success": "工艺编译未成功，脚本或规范存在问题。",
        }
        confirm_by_req = {
            str(item.get("requirement_id") or ""): item for item in (story_requirement_confirmations or [])
        }
        mapping = {
            "story_authenticity_two_trusted_sources": "R1_authenticity_two_trusted_interfaces",
            "story_standardized_completion_with_street": "R2_standardization_with_street",
            "story_token_graph_chain_present": "R3_tokenization_graph_chain",
        }

        rows: List[Dict[str, Any]] = []
        for check in failed_checks:
            req_id = mapping.get(check)
            req_item = confirm_by_req.get(req_id or "") if req_id else None
            rows.append(
                {
                    "check": check,
                    "passed": bool(checks.get(check)),
                    "reason": reason_templates.get(check, f"检查项 {check} 未通过。"),
                    "related_requirement": req_id,
                    "requirement_conclusion": (req_item or {}).get("conclusion") if req_item else None,
                    "requirement_evidence": (req_item or {}).get("evidence") if req_item else None,
                }
            )
        return rows

    @staticmethod
    def _persist_round(run_dir: Path, round_data: BootstrapRound, llm_events: Optional[List[Dict[str, Any]]] = None) -> Path:
        round_dir = run_dir / f"round_{round_data.round_index:02d}_{round_data.stage}"
        round_dir.mkdir(parents=True, exist_ok=True)

        result = round_data.result
        audit = round_data.audit
        process_doc = str(result.get("process_doc_markdown") or "")
        if process_doc:
            (round_dir / "process_doc.md").write_text(process_doc, encoding="utf-8")

        compilation = result.get("compilation") or {}
        scripts = compilation.get("tool_scripts") or {}
        if isinstance(scripts, dict):
            scripts_dir = round_dir / "tool_scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            for tool_name, code in scripts.items():
                safe = str(tool_name or "tool").strip().replace("/", "_")
                (scripts_dir / f"{safe}.py").write_text(str(code or ""), encoding="utf-8")

        (round_dir / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (round_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if llm_events:
            (round_dir / "llm_trace.json").write_text(json.dumps(llm_events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        round_md = ProcessExpertBootstrapRunner._build_round_process_markdown(round_data, round_dir)
        (round_dir / "process_artifact.md").write_text(round_md, encoding="utf-8")
        return round_dir

    @staticmethod
    def _build_round_process_markdown(round_data: BootstrapRound, round_dir: Optional[Path] = None) -> str:
        result = round_data.result or {}
        audit = round_data.audit or {}
        compilation = result.get("compilation") or {}
        process_spec = compilation.get("process_spec") or {}
        steps = (result.get("plan") or {}).get("steps") or []
        scripts = compilation.get("tool_scripts") or {}

        step_lines = []
        if isinstance(steps, list) and steps:
            for idx, step in enumerate(steps, start=1):
                step_lines.append(f"{idx}. {str(step)}")
        else:
            step_lines.append("1. 由编译器生成流程步骤（未返回结构化 steps）")

        checks = audit.get("checks") or {}
        condition_lines = []
        for key, value in checks.items():
            condition_lines.append(f"- `{key}`: {'通过' if bool(value) else '未通过'}")
        if not condition_lines:
            condition_lines.append("- 无审计条件")

        script_lines = []
        if isinstance(scripts, dict) and scripts:
            for tool_name, code in scripts.items():
                desc = ProcessExpertBootstrapRunner._extract_script_description(str(code or ""))
                script_file = (round_dir / "tool_scripts" / f"{str(tool_name or 'tool').strip().replace('/', '_')}.py") if round_dir else None
                script_path_text = str(script_file) if script_file else "(路径未知)"
                script_lines.append(f"- `{tool_name}`: {desc} | 脚本路径: `{script_path_text}`")
        else:
            script_lines.append("- 无工具脚本")

        code = str(result.get("process_code") or process_spec.get("code") or "UNKNOWN")
        name = str(result.get("process_name") or process_spec.get("name") or "未命名工艺")
        domain = str(result.get("domain") or process_spec.get("domain") or "unknown")

        return (
            f"# 工艺件（Round {round_data.round_index} - {round_data.stage}）\n\n"
            f"- 工艺编码: `{code}`\n"
            f"- 工艺名称: {name}\n"
            f"- 领域: {domain}\n"
            f"- 审计得分: {round_data.score}\n\n"
            "## 文字描述\n\n"
            "该工艺用于围绕地址用例驱动执行工具包生成流程，包含规划、编译、审计与迭代。"
            "本轮产物用于验证工艺是否满足可执行与可审计要求。\n\n"
            "## 流程步骤\n\n"
            + "\n".join(step_lines)
            + "\n\n## 关键条件判断\n\n"
            + "\n".join(condition_lines)
            + "\n\n## 调用脚本与说明\n\n"
            + "\n".join(script_lines)
            + "\n\n## Story审计确认\n\n"
            + "\n".join(
                [
                    f"- `{str(item.get('requirement_id') or '')}` {str(item.get('description') or '')}: {'通过' if bool(item.get('passed')) else '未通过'}（{str(item.get('conclusion') or '未明确')}）"
                    for item in list((audit.get("story_requirement_confirmations") or []))
                ]
                or ["- 无"]
            )
            + "\n\n## 未通过原因分析\n\n"
            + "\n".join(
                [
                    f"- `{str(item.get('check') or '')}`: {str(item.get('reason') or '')}"
                    for item in list((audit.get("failed_check_analysis") or []))
                ]
                or ["- 无"]
            )
            + "\n"
        )

    def _persist_workpackage_process_artifact(
        self,
        run_dir: Path,
        rounds: List[BootstrapRound],
        case_summary: Dict[str, Any],
    ) -> None:
        lines: List[str] = []
        lines.append("# 工艺件：完整工艺流程记录")
        lines.append("")
        lines.append(f"- 用例总量: {case_summary.get('total', 0)}")
        lines.append(f"- 轮次数: {len(rounds)}")
        lines.append("")
        lines.append("## 全局文字描述")
        lines.append("")
        lines.append("本工作包记录了基于地址用例的工艺生成与迭代过程，覆盖设计、修改、审计以及脚本产物。")
        lines.append("")

        for r in rounds:
            lines.append(f"## Round {r.round_index} ({r.stage})")
            lines.append("")
            lines.append(f"- 工艺编码: `{r.result.get('process_code')}`")
            lines.append(f"- 审计得分: {r.score}")
            lines.append(f"- 草案ID: `{r.result.get('draft_id')}`")
            lines.append("")
            lines.append("### 关键条件判断")
            checks = (r.audit or {}).get("checks") or {}
            if checks:
                for key, value in checks.items():
                    lines.append(f"- `{key}`: {'通过' if bool(value) else '未通过'}")
            else:
                lines.append("- 无")
            lines.append("")
            lines.append("### Story审计要求结果确认")
            confirmations = (r.audit or {}).get("story_requirement_confirmations") or []
            if confirmations:
                for item in confirmations:
                    lines.append(
                        f"- `{item.get('requirement_id')}` {item.get('description')}: "
                        f"{'通过' if bool(item.get('passed')) else '未通过'}（{item.get('conclusion') or '未明确'}）"
                    )
            else:
                lines.append("- 无")
            lines.append("")
            lines.append("### 未通过原因及分析")
            analysis_items = (r.audit or {}).get("failed_check_analysis") or []
            if analysis_items:
                for item in analysis_items:
                    lines.append(f"- `{item.get('check')}`: {item.get('reason')}")
            else:
                lines.append("- 无")
            lines.append("")
            lines.append("### 调用脚本与说明")
            scripts = ((r.result.get("compilation") or {}).get("tool_scripts") or {})
            if isinstance(scripts, dict) and scripts:
                for tool_name, code in scripts.items():
                    snippet = self._extract_script_description(str(code or ""))
                    round_dir = r.round_dir or (run_dir / f"round_{r.round_index:02d}_{r.stage}")
                    script_file = round_dir / "tool_scripts" / f"{str(tool_name or 'tool').strip().replace('/', '_')}.py"
                    lines.append(f"- `{tool_name}`: {snippet} | 路径: `{script_file}`")
            else:
                lines.append("- 无")
            lines.append("")

        lines.append("## 执行流程脚本位置")
        lines.append("")
        lines.append(f"- 主执行入口: `{Path(__file__).resolve().parent.parent / 'scripts' / 'run_process_expert_bootstrap.py'}`")
        lines.append(f"- LLM桥接脚本: `{Path(__file__).resolve().parent.parent / 'tools' / 'process_expert_llm_bridge.py'}`")
        lines.append(f"- 工艺引擎脚本: `{Path(__file__).resolve().parent.parent / 'tools' / 'process_expert_bootstrap.py'}`")
        lines.append("")

        (run_dir / "workpackage_process_artifact.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _extract_script_description(script_text: str) -> str:
        if not script_text.strip():
            return "自动生成脚本"
        for ln in script_text.splitlines():
            t = ln.strip()
            if not t:
                continue
            if t in {'"""', "'''"}:
                continue
            if t.startswith("#"):
                cleaned = t.lstrip("#").strip()
                if cleaned:
                    return cleaned[:120]
                continue
            if t.startswith("def ") or t.startswith("class "):
                return t[:120]
            if t.startswith("import ") or t.startswith("from "):
                continue
            return t[:120]
        return "自动生成脚本"
