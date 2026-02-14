#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib import error, request


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _load_cases(cases_file: Path) -> Dict[str, Any]:
    with cases_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def _post_json(url: str, payload: Dict[str, Any], timeout: int) -> Tuple[int, Dict[str, Any], str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), _safe_json_loads(raw), raw
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return int(exc.code), _safe_json_loads(raw), raw
    except Exception as exc:
        return 0, {"status": "error", "error": str(exc)}, str(exc)


def _safe_json_loads(text: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return {"status": "error", "error": "response is not object", "raw": parsed}
    except Exception:
        return {"status": "error", "error": "invalid json response", "raw": text}


def _build_requirement(case: Dict[str, Any]) -> str:
    case_id = str(case.get("case_id") or "unknown")
    category = str(case.get("category") or "unknown")
    priority = str(case.get("priority") or "P2")
    target_stage = str(case.get("target_stage") or "unknown")
    expected_iteration_action = str(case.get("expected_iteration_action") or "none")

    return (
        "请你作为地址产线工艺专家Agent，根据以下质量审计用例生成或迭代工艺草案。\n"
        "要求：\n"
        "1) 覆盖标准化、关联融合、证据链输出、门禁策略；\n"
        "2) 对缺失能力给出降级与补充路径；\n"
        "3) 工具链需可编译并输出 process_spec 与 tool_scripts。\n\n"
        f"用例ID: {case_id}\n"
        f"优先级: {priority}\n"
        f"分类: {category}\n"
        f"目标阶段: {target_stage}\n"
        f"预期迭代动作: {expected_iteration_action}\n"
        f"输入: {json.dumps(case.get('input') or {}, ensure_ascii=False)}\n"
        f"期望: {json.dumps(case.get('expected') or {}, ensure_ascii=False)}\n"
        f"审计关注点: {json.dumps(case.get('audit_focus') or [], ensure_ascii=False)}\n"
        f"目标工具: {json.dumps(case.get('target_tools') or [], ensure_ascii=False)}\n"
    )


def _evaluate_case(case: Dict[str, Any], resp: Dict[str, Any], http_status: int) -> Dict[str, Any]:
    priority = str(case.get("priority") or "P2")
    compilation = resp.get("compilation") if isinstance(resp, dict) else {}
    if not isinstance(compilation, dict):
        compilation = {}

    has_compilation = bool(compilation)
    has_process_spec = bool(compilation.get("process_spec"))
    tool_scripts = compilation.get("tool_scripts")
    has_tool_scripts = isinstance(tool_scripts, dict) and len(tool_scripts) > 0
    readiness = str(compilation.get("execution_readiness") or "unknown")
    compile_success = bool(compilation.get("success"))

    passed = False
    fail_reason = ""

    if http_status != 200:
        fail_reason = f"http_status={http_status}"
    elif str(resp.get("status")) != "ok":
        fail_reason = f"status={resp.get('status')}"
    elif priority == "P0":
        passed = compile_success and has_process_spec and has_tool_scripts and readiness in {"ready", "partial"}
        if not passed:
            fail_reason = "P0审计未满足编译/可执行性要求"
    else:
        passed = compile_success and has_process_spec
        if not passed:
            fail_reason = "编译结果不完整"

    return {
        "case_id": case.get("case_id"),
        "priority": priority,
        "http_status": http_status,
        "status": resp.get("status"),
        "draft_id": resp.get("draft_id"),
        "process_code": resp.get("process_code"),
        "compile_success": compile_success,
        "execution_readiness": readiness,
        "has_process_spec": has_process_spec,
        "has_tool_scripts": has_tool_scripts,
        "validation_errors": compilation.get("validation_errors") or [],
        "validation_warnings": compilation.get("validation_warnings") or [],
        "pass": passed,
        "fail_reason": fail_reason,
        "error": resp.get("error"),
    }


def _build_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.get("pass"))
    failed = total - passed
    by_priority: Dict[str, Dict[str, int]] = {}
    for r in results:
        p = str(r.get("priority") or "unknown")
        by_priority.setdefault(p, {"total": 0, "passed": 0, "failed": 0})
        by_priority[p]["total"] += 1
        if r.get("pass"):
            by_priority[p]["passed"] += 1
        else:
            by_priority[p]["failed"] += 1
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": (passed / total) if total else 0.0,
        "by_priority": by_priority,
    }


def _write_markdown(path: Path, summary: Dict[str, Any], results: List[Dict[str, Any]], run_meta: Dict[str, Any]) -> None:
    lines: List[str] = []
    lines.append("# 地址产线质量审计回归报告")
    lines.append("")
    lines.append(f"- run_id: {run_meta.get('run_id')}")
    lines.append(f"- base_url: {run_meta.get('base_url')}")
    lines.append(f"- cases_file: {run_meta.get('cases_file')}")
    lines.append(f"- started_at: {run_meta.get('started_at')}")
    lines.append(f"- finished_at: {run_meta.get('finished_at')}")
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append(f"- total: {summary.get('total')}")
    lines.append(f"- passed: {summary.get('passed')}")
    lines.append(f"- failed: {summary.get('failed')}")
    lines.append(f"- pass_rate: {summary.get('pass_rate'):.2%}")
    lines.append("")
    lines.append("## 分优先级")
    lines.append("")
    for key in sorted((summary.get("by_priority") or {}).keys()):
        item = summary["by_priority"][key]
        lines.append(f"- {key}: {item['passed']}/{item['total']} (failed={item['failed']})")
    lines.append("")
    lines.append("## 失败用例")
    lines.append("")
    failed_cases = [r for r in results if not r.get("pass")]
    if not failed_cases:
        lines.append("- 无")
    else:
        for r in failed_cases:
            lines.append(
                f"- {r.get('case_id')}: {r.get('fail_reason') or r.get('error') or 'unknown'} "
                f"(readiness={r.get('execution_readiness')}, compile_success={r.get('compile_success')})"
            )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="地址产线质量审计回归执行器（调用 process expert design）")
    parser.add_argument(
        "--allow-llm-governance",
        action="store_true",
        help="显式允许调用 process expert design（默认禁用，符合离线工具包版本约束）",
    )
    parser.add_argument(
        "--cases-file",
        default="testdata/fixtures/address-line-quality-audit-cases-2026-02-14.json",
        help="用例文件路径",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8081", help="Agent 服务地址")
    parser.add_argument("--domain", default="verification", help="design 请求 domain")
    parser.add_argument("--timeout", type=int, default=90, help="单次请求超时秒数")
    parser.add_argument("--max-cases", type=int, default=0, help="限制执行条数，0表示全部")
    parser.add_argument("--output-dir", default="output", help="报告输出目录")
    args = parser.parse_args()

    if not args.allow_llm_governance:
        print("[BLOCKED] 当前版本为离线工具包治理模式，默认禁用 LLM 治理回归。")
        print("[BLOCKED] 如需兼容旧链路，请显式加参数: --allow-llm-governance")
        return 3

    root = Path(__file__).resolve().parent.parent
    cases_file = (root / args.cases_file).resolve() if not Path(args.cases_file).is_absolute() else Path(args.cases_file)
    output_dir = (root / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not cases_file.exists():
        print(f"[ERROR] cases file not found: {cases_file}")
        return 2

    dataset = _load_cases(cases_file)
    cases = list(dataset.get("cases") or [])
    if args.max_cases and args.max_cases > 0:
        cases = cases[: args.max_cases]

    if not cases:
        print("[ERROR] no cases to run")
        return 2

    started_at = datetime.now().isoformat()
    run_id = f"address_audit_{_now_tag()}"
    endpoint = args.base_url.rstrip("/") + "/api/v1/process/expert/chat"

    results: List[Dict[str, Any]] = []
    for idx, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id") or f"case_{idx}")
        requirement = _build_requirement(case)
        payload = {
            "action": "design",
            "requirement": requirement,
            "domain": args.domain,
            "goal": f"通过质量审计用例 {case_id}",
        }

        t0 = time.time()
        http_status, resp, _raw = _post_json(endpoint, payload, timeout=args.timeout)
        elapsed_ms = int((time.time() - t0) * 1000)
        evaluated = _evaluate_case(case, resp, http_status)
        evaluated["elapsed_ms"] = elapsed_ms
        results.append(evaluated)
        print(
            f"[{idx}/{len(cases)}] {case_id} -> pass={evaluated['pass']} "
            f"status={evaluated.get('status')} readiness={evaluated.get('execution_readiness')} "
            f"elapsed={elapsed_ms}ms"
        )

    summary = _build_summary(results)
    finished_at = datetime.now().isoformat()
    run_meta = {
        "run_id": run_id,
        "base_url": args.base_url,
        "cases_file": str(cases_file),
        "started_at": started_at,
        "finished_at": finished_at,
    }

    file_tag = _now_tag()
    json_path = output_dir / f"address_line_quality_audit_{file_tag}.json"
    md_path = output_dir / f"address_line_quality_audit_{file_tag}.md"

    json_payload = {
        "meta": run_meta,
        "summary": summary,
        "results": results,
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_markdown(md_path, summary, results, run_meta)

    print(f"[DONE] report(json): {json_path}")
    print(f"[DONE] report(md):   {md_path}")
    print(
        f"[DONE] pass_rate={summary['pass_rate']:.2%} "
        f"({summary['passed']}/{summary['total']})"
    )

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
