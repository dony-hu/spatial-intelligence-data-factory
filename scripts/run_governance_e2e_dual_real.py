#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.agent_cli import load_config, run_requirement_query
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _extract_json_object(text: str) -> Dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        raise RuntimeError("llm answer empty")
    candidates = [raw]
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw, flags=re.IGNORECASE)
    if fenced:
        candidates.append(fenced.group(1))
    braced = re.search(r"(\{[\s\S]*\})", raw)
    if braced:
        candidates.append(braced.group(1))
    for item in candidates:
        try:
            parsed = json.loads(item)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue
    raise RuntimeError("llm answer does not contain valid json object")


def _load_trusted_sources() -> Dict[str, Any]:
    path = PROJECT_ROOT / "config" / "trusted_data_sources.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_fengtu_interfaces(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    for src in list(config.get("trusted_sources") or []):
        if str(src.get("source_id")) == "fengtu":
            interfaces = list(src.get("trusted_interfaces") or [])
            if interfaces:
                return interfaces
    raise RuntimeError("fengtu trusted_interfaces not found in trusted_data_sources.json")


def _build_case_records(max_cases: int) -> List[Dict[str, Any]]:
    matrix_path = PROJECT_ROOT / "testdata" / "fixtures" / "address-pipeline-case-matrix-2026-02-12.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    cases = list(matrix.get("cases") or [])
    records: List[Dict[str, Any]] = []
    for item in cases:
        if len(records) >= max_cases:
            break
        raw = str((item.get("input") or {}).get("raw") or (item.get("input") or {}).get("address") or "").strip()
        if not raw:
            continue
        case_id = str(item.get("case_id") or f"case_{len(records)+1}")
        records.append(
            {
                "raw_id": f"dual-{case_id}",
                "raw_text": raw,
                "province": "广东省",
                "city": "深圳市",
                "county": "南山区",
                "town": "南山街道",
                "citycode": "755",
                "company": "顺丰",
            }
        )
    if not records:
        raise RuntimeError("no address records found for e2e")
    return records


def _generate_workpackage_with_llm(llm_cfg: Dict[str, Any], requirement: str, interfaces: List[Dict[str, Any]]) -> Dict[str, Any]:
    interface_meta = [
        {
            "interface_id": it.get("interface_id"),
            "name": it.get("name"),
            "method": it.get("method"),
            "base_url": it.get("base_url"),
            "request_template": it.get("request_template"),
        }
        for it in interfaces
    ]
    prompt = (
        "你是地址治理工厂的工艺规划器。\n"
        "请基于需求与可信地图接口元数据，输出JSON对象（不要输出解释文字），字段必须包含:\n"
        "workpackage_name, process_goal, interface_sequence(数组，元素为interface_id),\n"
        "governance_steps(数组), output_contract(对象，至少含raw_id/canon_text/confidence/evidence)。\n"
        f"需求: {requirement}\n"
        f"可信接口: {json.dumps(interface_meta, ensure_ascii=False)}"
    )
    llm_result = run_requirement_query(requirement=prompt, config=llm_cfg)
    obj = _extract_json_object(llm_result.get("answer"))
    seq = obj.get("interface_sequence")
    if not isinstance(seq, list) or not seq:
        raise RuntimeError("llm workpackage missing interface_sequence")
    return obj


def _write_workpackage_executor(script_path: Path, trusted_cfg_path: Path) -> None:
    code = f'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
from urllib import parse, request


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_interface(trusted_cfg: Dict[str, Any], interface_id: str) -> Dict[str, Any]:
    for src in list(trusted_cfg.get("trusted_sources") or []):
        for it in list(src.get("trusted_interfaces") or []):
            if str(it.get("interface_id")) == str(interface_id):
                return dict(it)
    raise RuntimeError(f"interface not found: {{interface_id}}")


def _fill_template(value: Any, record: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        out = value
        for k, v in record.items():
            out = out.replace("{" + str(k) + "}", str(v))
        return out
    if isinstance(value, dict):
        return {{k: _fill_template(v, record) for k, v in value.items()}}
    if isinstance(value, list):
        return [_fill_template(v, record) for v in value]
    return value


def _call_interface(it: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    method = str(it.get("method") or "GET").upper()
    base_url = str(it.get("base_url") or "").strip()
    headers = dict(it.get("headers") or {{}})
    template = dict(it.get("request_template") or {{}})
    query = _fill_template(template.get("query") or {{}}, record)
    body = _fill_template(template.get("body") or {{}}, record)

    if str(it.get("ak_in") or "").lower() == "query" and "ak" not in query and "ak" in headers:
        query["ak"] = headers["ak"]
        headers = {{k: v for k, v in headers.items() if k.lower() != "ak"}}

    url = base_url
    if query:
        url = f"{{base_url}}?{{parse.urlencode(query)}}"

    data = None
    if method in {{"POST", "PUT", "PATCH"}}:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    req = request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw)
            return {{"ok": True, "http_status": int(resp.status), "body": payload}}
    except Exception as exc:
        return {{"ok": False, "error": str(exc)}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute generated address governance workpackage")
    parser.add_argument("--workpackage", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    wp = _load_json(Path(args.workpackage))
    cases = _load_json(Path(args.cases))
    trusted_cfg = _load_json(Path("{trusted_cfg_path.as_posix()}"))

    sequence = list(wp.get("interface_sequence") or [])
    records = list(cases.get("records") or [])
    outputs: List[Dict[str, Any]] = []

    for rec in records:
        evidence_items: List[Dict[str, Any]] = []
        ok_count = 0
        for interface_id in sequence:
            it = _find_interface(trusted_cfg, str(interface_id))
            res = _call_interface(it, rec)
            if res.get("ok"):
                ok_count += 1
            evidence_items.append({{
                "interface_id": interface_id,
                "ok": bool(res.get("ok")),
                "result": res,
            }})

        confidence = (ok_count / len(sequence)) if sequence else 0.0
        outputs.append({{
            "raw_id": rec.get("raw_id"),
            "canon_text": str(rec.get("raw_text") or "").strip(),
            "confidence": round(float(confidence), 4),
            "strategy": "trusted_interface_chain",
            "evidence": {{"items": evidence_items}},
        }})

    out = {{"results": outputs, "sequence": sequence}}
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    script_path.write_text(code, encoding="utf-8")
    script_path.chmod(0o755)


def _persist_to_pg(task_id: str, batch_name: str, records: List[Dict[str, Any]], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    db_url = str(os.getenv("DATABASE_URL") or "")
    if not db_url.startswith("postgresql"):
        raise RuntimeError(
            "DATABASE_URL must be postgresql for this e2e. "
            "Example: export DATABASE_URL='postgresql://user:pass@127.0.0.1:5432/addr_governance'"
        )

    REPOSITORY.create_task(
        task_id=task_id,
        batch_name=batch_name,
        ruleset_id="default",
        status="PENDING",
        queue_backend="workpackage_script",
        queue_message="generated_script",
    )
    REPOSITORY.save_results(task_id=task_id, results=results, raw_records=records)
    REPOSITORY.set_task_status(task_id, "SUCCEEDED")
    REPOSITORY.upsert_review(task_id, {"raw_id": records[0].get("raw_id"), "review_status": "approved", "reviewer": "e2e"})
    REPOSITORY.reconcile_review(task_id, {"raw_id": records[0].get("raw_id"), "review_status": "approved", "reviewer": "e2e"})

    try:
        from sqlalchemy import create_engine, text
    except Exception:
        raise RuntimeError("sqlalchemy is required for PG persistence; install: /Users/huda/Code/.venv/bin/python -m pip install sqlalchemy")

    engine = create_engine(db_url)
    with engine.begin() as conn:
        task_rows = conn.execute(
            text("SELECT status FROM addr_task_run WHERE task_id = :task_id"),
            {"task_id": task_id},
        ).fetchall()
        raw_rows = conn.execute(
            text("SELECT COUNT(1) FROM addr_raw WHERE batch_id = :batch_id"),
            {"batch_id": task_id},
        ).scalar()
        canon_rows = conn.execute(
            text(
                """
                SELECT COUNT(1)
                FROM addr_canonical c
                JOIN addr_raw r ON c.raw_id = r.raw_id
                WHERE r.batch_id = :batch_id
                """
            ),
            {"batch_id": task_id},
        ).scalar()

    return {
        "task_status": task_rows[0][0] if task_rows else "MISSING",
        "raw_count": int(raw_rows or 0),
        "canonical_count": int(canon_rows or 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Dual-perspective real E2E: LLM workpackage + production script + PG persistence")
    parser.add_argument("--llm-config", default="config/llm_api.json")
    parser.add_argument("--max-cases", type=int, default=6)
    parser.add_argument("--output-dir", default="output/e2e_dual_real")
    parser.add_argument("--human-reviewer", default="factory-user", help="Human reviewer name")
    parser.add_argument("--human-decision", choices=["approve", "reject"], default="approve")
    parser.add_argument("--human-note", default="工作包通过人工评审，允许产线执行")
    parser.add_argument(
        "--requirement",
        default="生成可执行的地址治理工作包，使用可信地图接口链路完成地址核验并落库",
    )
    args = parser.parse_args()

    out_root = (PROJECT_ROOT / args.output_dir).resolve()
    run_dir = out_root / f"dual_e2e_{_now_tag()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    llm_cfg = load_config(str((PROJECT_ROOT / args.llm_config).resolve()))
    trusted_cfg = _load_trusted_sources()
    interfaces = _pick_fengtu_interfaces(trusted_cfg)

    workpackage = _generate_workpackage_with_llm(llm_cfg, args.requirement, interfaces)
    interface_ids = list(workpackage.get("interface_sequence") or [])
    valid_ids = {str(it.get("interface_id")) for it in interfaces}
    filtered_ids = [str(x) for x in interface_ids if str(x) in valid_ids]
    if not filtered_ids:
        raise RuntimeError("llm selected no valid trusted interfaces")
    workpackage["interface_sequence"] = filtered_ids
    workpackage["created_at"] = datetime.now().isoformat()
    workpackage["trusted_source"] = "fengtu"
    workpackage["executor_generation_mode"] = "template_from_llm_interface_sequence"

    workpackage_path = run_dir / "workpackage.generated.json"
    workpackage_path.write_text(json.dumps(workpackage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    human_decision = {
        "reviewer": args.human_reviewer,
        "decision": args.human_decision,
        "note": args.human_note,
        "reviewed_at": datetime.now().isoformat(),
    }
    (run_dir / "human_decision.json").write_text(
        json.dumps(human_decision, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.human_decision != "approve":
        report = {
            "run_dir": str(run_dir),
            "angle_1_human_llm_workpackage": {
                "requirement": args.requirement,
                "workpackage_path": str(workpackage_path),
                "interface_sequence": filtered_ids,
                "human_decision": human_decision,
            },
            "angle_2_production_execution_and_pg": {
                "status": "blocked_by_human_decision",
            },
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    cases = {"records": _build_case_records(max_cases=args.max_cases)}
    cases_path = run_dir / "address_cases.json"
    cases_path.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    executor_path = run_dir / "workpackage_executor.py"
    _write_workpackage_executor(executor_path, PROJECT_ROOT / "config" / "trusted_data_sources.json")

    execution_output_path = run_dir / "workpackage_execution_output.json"
    cmd = [
        sys.executable,
        str(executor_path),
        "--workpackage",
        str(workpackage_path),
        "--cases",
        str(cases_path),
        "--output",
        str(execution_output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"workpackage executor failed: {proc.stderr or proc.stdout}")

    execution_payload = json.loads(execution_output_path.read_text(encoding="utf-8"))
    results = list(execution_payload.get("results") or [])
    if not results:
        raise RuntimeError("workpackage execution produced empty results")

    task_id = f"task_dual_{_now_tag()}"
    pg_summary = _persist_to_pg(
        task_id=task_id,
        batch_name=f"batch_{task_id}",
        records=list(cases.get("records") or []),
        results=results,
    )

    report = {
        "run_dir": str(run_dir),
        "angle_1_human_llm_workpackage": {
            "requirement": args.requirement,
            "workpackage_path": str(workpackage_path),
            "executor_script_path": str(executor_path),
            "interface_sequence": filtered_ids,
            "human_decision": human_decision,
        },
        "angle_2_production_execution_and_pg": {
            "task_id": task_id,
            "cases_count": len(cases.get("records") or []),
            "execution_output_path": str(execution_output_path),
            "pg_summary": pg_summary,
        },
    }
    report_path = run_dir / "dual_e2e_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
