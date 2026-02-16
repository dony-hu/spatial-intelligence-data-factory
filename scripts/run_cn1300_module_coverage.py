#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.address_core.dedup import dedup_records
from packages.address_core.match import recall_candidates
from packages.address_core.normalize import normalize_text
from packages.address_core.parse import parse_components
from packages.address_core.score import score_confidence


DEFAULT_DATASET = Path("testdata/fixtures/lab-mode-phase1_5-中文地址测试用例-1300-2026-02-15.csv")
DEFAULT_OUTPUT_DIR = Path("output/lab_mode")


@dataclass
class RowResult:
    case_id: str
    raw_text: str
    expected_normalized: str
    normalized: str
    normalize_hit: bool
    parse_hits: dict[str, bool]
    match_hit: bool
    confidence: float
    strategy: str
    expected_judgement: str
    predicted_judgement: str
    score_hit: bool
    fengtu_conflict_pending: bool
    fengtu_candidate: str
    case_type: str
    scenario_tag: str
    city: str
    district: str
    expected_human_review: bool


def _canon_text(text: str) -> str:
    return str(text or "").replace(" ", "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _as_bool(value: str) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "y", "yes", "true", "是", "需", "需要"}


def _load_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader, start=1):
            rows.append({str(k): str(v or "") for k, v in row.items()})
            if limit and idx >= limit:
                break
    return rows


def _expected_for_parse(row: dict[str, str]) -> dict[str, str]:
    return {
        "province": row.get("省", ""),
        "city": row.get("市", ""),
        "district": row.get("区县", ""),
        # Current parse module only exposes road/house_no; road baseline aligns to street column.
        "road": row.get("街道", ""),
        "house_no": row.get("门牌号", ""),
    }


def _label_from_strategy(strategy: str) -> str:
    if strategy == "rule_only":
        return "accept"
    if strategy == "match_dict":
        return "needs-human"
    return "reject"


def _eval_row(row: dict[str, str]) -> RowResult:
    raw_text = row.get("原始地址", "")
    expected_normalized = row.get("预期标准化地址", "")
    expected_judgement = row.get("预期判定", "")
    expected_human_review = _as_bool(row.get("是否需人工复核", ""))

    normalized = normalize_text(raw_text)
    normalize_hit = _canon_text(normalized) == _canon_text(expected_normalized)

    parsed = parse_components(normalized)
    expected_parse = _expected_for_parse(row)
    parse_hits: dict[str, bool] = {}
    for field_name, expected_value in expected_parse.items():
        expected = _canon_text(expected_value)
        got = _canon_text(parsed.get(field_name, ""))
        parse_hits[field_name] = bool(expected) and got == expected

    candidates = recall_candidates(normalized)
    expected_canon = _canon_text(expected_normalized)
    match_hit = any(_canon_text(getattr(candidate, "name", "")) == expected_canon for candidate in candidates)
    fengtu_names = [str(getattr(candidate, "name", "")) for candidate in candidates if str(getattr(candidate, "source", "")) == "fengtu_standardize"]
    fengtu_candidate = fengtu_names[0] if fengtu_names else ""
    fengtu_conflict_pending = bool(fengtu_candidate) and _canon_text(fengtu_candidate) != expected_canon

    confidence, strategy = score_confidence(parsed, candidates)
    predicted_judgement = _label_from_strategy(strategy)
    score_hit = predicted_judgement == expected_judgement

    return RowResult(
        case_id=row.get("case_id", ""),
        raw_text=raw_text,
        expected_normalized=expected_normalized,
        normalized=normalized,
        normalize_hit=normalize_hit,
        parse_hits=parse_hits,
        match_hit=match_hit,
        confidence=confidence,
        strategy=strategy,
        expected_judgement=expected_judgement,
        predicted_judgement=predicted_judgement,
        score_hit=score_hit,
        fengtu_conflict_pending=fengtu_conflict_pending,
        fengtu_candidate=fengtu_candidate,
        case_type=row.get("用例类型", "") or "unknown",
        scenario_tag=row.get("场景标签", "") or "unknown",
        city=row.get("市", "") or "unknown",
        district=row.get("区县", "") or "unknown",
        expected_human_review=expected_human_review,
    )


def _eval_dedup(rows: list[dict[str, str]]) -> dict[str, Any]:
    def _variant_of(raw_text: str) -> str:
        text = str(raw_text or "")
        changed = text
        if "栋" in changed:
            changed = changed.replace("栋", "幢", 1)
        elif "幢" in changed:
            changed = changed.replace("幢", "栋", 1)

        prefixes = [
            ("广东省深圳市", "深圳市"),
            ("江苏省苏州市", "苏州市"),
            ("湖北省武汉市", "武汉市"),
            ("湖北省随州市", "随州市"),
        ]
        for full, short in prefixes:
            if changed.startswith(full):
                changed = short + changed[len(full) :]
                break

        if "号" in changed:
            changed = changed.replace("号", "号 ", 1)
        return changed

    dedup_input: list[dict[str, str]] = []
    injected_exact = 0
    injected_variant = 0
    for idx, row in enumerate(rows):
        raw_text = row.get("原始地址", "")
        dedup_input.append({"raw_id": row.get("case_id", f"case-{idx}"), "raw_text": raw_text})

        # Inject deterministic duplicates to validate dedup behavior.
        if idx % 10 == 0:
            injected_exact += 1
            dedup_input.append({"raw_id": f"{row.get('case_id', f'case-{idx}')}-dup", "raw_text": raw_text})

        # Inject normalized variants and only count when normalized hash is equivalent.
        if idx % 8 == 0:
            variant = _variant_of(raw_text)
            if _canon_text(variant) != _canon_text(raw_text):
                if _canon_text(normalize_text(variant)) == _canon_text(normalize_text(raw_text)):
                    injected_variant += 1
                    dedup_input.append({"raw_id": f"{row.get('case_id', f'case-{idx}')}-var", "raw_text": variant})

    unique = dedup_records(dedup_input)
    injected_duplicates = injected_exact + injected_variant
    removed_duplicates = len(dedup_input) - len(unique)
    return {
        "input_count": len(dedup_input),
        "expected_unique_count": len(rows),
        "output_unique_count": len(unique),
        "injected_exact_duplicates": injected_exact,
        "injected_variant_duplicates": injected_variant,
        "injected_duplicates": injected_duplicates,
        "removed_duplicates": removed_duplicates,
        "dedup_exact_pass": removed_duplicates == injected_duplicates and len(unique) == len(rows),
    }


def _build_report(
    dataset_path: Path,
    rows: list[dict[str, str]],
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    row_results: list[RowResult] = []
    total_rows = len(rows)
    for idx, row in enumerate(rows, start=1):
        row_results.append(_eval_row(row))
        if progress_callback and (idx == 1 or idx % 20 == 0 or idx == total_rows):
            progress_callback(idx, total_rows, str(row.get("case_id", "")))
    total = len(row_results)
    if total <= 0:
        raise ValueError("dataset is empty")

    normalize_hits = sum(1 for item in row_results if item.normalize_hit)
    match_hits = sum(1 for item in row_results if item.match_hit)
    score_hits = sum(1 for item in row_results if item.score_hit)
    fengtu_conflict_pending_count = sum(1 for item in row_results if item.fengtu_conflict_pending)

    parse_field_names = ["province", "city", "district", "road", "house_no"]
    parse_hits_by_field: dict[str, int] = {key: 0 for key in parse_field_names}
    for item in row_results:
        for field_name in parse_field_names:
            if item.parse_hits.get(field_name):
                parse_hits_by_field[field_name] += 1

    confidences = [item.confidence for item in row_results]
    strategy_counter = Counter(item.strategy for item in row_results)
    expected_counter = Counter(item.expected_judgement for item in row_results)
    predicted_counter = Counter(item.predicted_judgement for item in row_results)
    overall_result_counter = Counter(
        "pass" if (item.normalize_hit and all(item.parse_hits.values()) and item.match_hit and item.score_hit) else "fail"
        for item in row_results
    )
    case_type_counter = Counter(item.case_type for item in row_results)
    city_counter = Counter(item.city for item in row_results)

    case_details: list[dict[str, Any]] = []
    for item in row_results:
        parse_missing_fields = [field_name for field_name, hit in item.parse_hits.items() if not hit]
        overall_result = (
            "pass" if (item.normalize_hit and all(item.parse_hits.values()) and item.match_hit and item.score_hit) else "fail"
        )
        predicted_human_review = item.predicted_judgement == "needs-human"
        case_details.append(
            {
                "case_id": item.case_id,
                "case_type": item.case_type,
                "scenario_tag": item.scenario_tag,
                "city": item.city,
                "district": item.district,
                "raw_text": item.raw_text,
                "normalized": item.normalized,
                "expected_normalized": item.expected_normalized,
                "overall_result": overall_result,
                "module_result": {
                    "normalize": item.normalize_hit,
                    "parse": all(item.parse_hits.values()),
                    "match": item.match_hit,
                    "score": item.score_hit,
                },
                "parse_field_hits": item.parse_hits,
                "parse_missing_fields": parse_missing_fields,
                "strategy": item.strategy,
                "confidence": item.confidence,
                "expected_judgement": item.expected_judgement,
                "predicted_judgement": item.predicted_judgement,
                "expected_human_review": item.expected_human_review,
                "predicted_human_review": predicted_human_review,
                "status": "completed",
                "fengtu_conflict_pending": item.fengtu_conflict_pending,
                "fengtu_candidate": item.fengtu_candidate,
            }
        )

    worst_normalize = [
        {
            "case_id": item.case_id,
            "raw_text": item.raw_text,
            "expected_normalized": item.expected_normalized,
            "normalized": item.normalized,
        }
        for item in row_results
        if not item.normalize_hit
    ][:20]
    worst_score = [
        {
            "case_id": item.case_id,
            "expected_judgement": item.expected_judgement,
            "predicted_judgement": item.predicted_judgement,
            "confidence": item.confidence,
            "strategy": item.strategy,
        }
        for item in row_results
        if not item.score_hit
    ][:20]
    fengtu_conflicts = [
        {
            "case_id": item.case_id,
            "raw_text": item.raw_text,
            "expected_normalized": item.expected_normalized,
            "fengtu_candidate": item.fengtu_candidate,
            "note": "pending_user_confirmation",
        }
        for item in row_results
        if item.fengtu_conflict_pending
    ][:50]

    return {
        "dataset": str(dataset_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows_total": total,
        "execution": {
            "status": "completed",
            "processed_rows": total,
            "total_rows": total,
            "progress_rate": 1.0,
        },
        "module_coverage": {
            "normalize": {
                "hit_count": normalize_hits,
                "hit_rate": round(normalize_hits / total, 6),
            },
            "parse": {
                "field_hit_count": parse_hits_by_field,
                "field_hit_rate": {key: round(value / total, 6) for key, value in parse_hits_by_field.items()},
            },
            "match": {
                "hit_count": match_hits,
                "hit_rate": round(match_hits / total, 6),
            },
            "dedup": _eval_dedup(rows),
            "score": {
                "judgement_hit_count": score_hits,
                "judgement_hit_rate": round(score_hits / total, 6),
                "fengtu_conflict_pending_count": fengtu_conflict_pending_count,
                "strategy_distribution": dict(strategy_counter),
                "expected_distribution": dict(expected_counter),
                "predicted_distribution": dict(predicted_counter),
                "confidence_stats": {
                    "mean": round(mean(confidences), 6),
                    "median": round(median(confidences), 6),
                    "min": round(min(confidences), 6),
                    "max": round(max(confidences), 6),
                    "p95": round(sorted(confidences)[int(total * 0.95) - 1], 6),
                },
            },
        },
        "case_summary": {
            "overall_result_distribution": dict(overall_result_counter),
            "case_type_distribution": dict(case_type_counter),
            "city_distribution_top20": dict(city_counter.most_common(20)),
        },
        "case_details": case_details,
        "samples": {
            "normalize_mismatch_top20": worst_normalize,
            "score_mismatch_top20": worst_score,
            "fengtu_conflicts_pending_confirmation_top50": fengtu_conflicts,
        },
        "phase2_note": "human review tiering refinement intentionally deferred",
}


def _write_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"cn1300_module_coverage_{stamp}.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def _write_progress(progress_file: Path | None, payload: dict[str, Any]) -> None:
    if progress_file is None:
        return
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    progress_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run module-level coverage report on CN address 1300 dataset")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="CSV dataset path")
    parser.add_argument("--limit", type=int, default=None, help="Optional row limit for quick local debug")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for report JSON")
    parser.add_argument("--enable-fengtu", action="store_true", help="Enable trusted Fengtu interfaces for match/score")
    parser.add_argument("--progress-file", default="", help="Optional progress json output path")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        raise FileNotFoundError(f"dataset not found: {dataset_path}")

    if args.enable_fengtu:
        os.environ["ADDRESS_TRUSTED_FENGTU_ENABLED"] = "1"

    progress_file = Path(args.progress_file) if args.progress_file else None
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        rows = _load_rows(dataset_path, limit=args.limit)
        total_rows = len(rows)
        _write_progress(
            progress_file,
            {
                "status": "running",
                "started_at": started_at,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "processed_rows": 0,
                "total_rows": total_rows,
                "progress_rate": 0.0 if total_rows > 0 else 1.0,
                "last_case_id": "",
                "report_path": "",
                "message": "coverage run started",
            },
        )

        def _progress_callback(processed: int, total: int, case_id: str) -> None:
            _write_progress(
                progress_file,
                {
                    "status": "running",
                    "started_at": started_at,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "processed_rows": processed,
                    "total_rows": total,
                    "progress_rate": round((processed / total), 6) if total > 0 else 1.0,
                    "last_case_id": case_id,
                    "report_path": "",
                    "message": "evaluating cases",
                },
            )

        report = _build_report(dataset_path=dataset_path, rows=rows, progress_callback=_progress_callback)
        report_path = _write_report(report=report, output_dir=Path(args.output_dir))
        _write_progress(
            progress_file,
            {
                "status": "completed",
                "started_at": started_at,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "processed_rows": len(rows),
                "total_rows": len(rows),
                "progress_rate": 1.0,
                "last_case_id": "",
                "report_path": str(report_path),
                "message": "coverage run completed",
            },
        )
    except Exception as exc:
        _write_progress(
            progress_file,
            {
                "status": "failed",
                "started_at": started_at,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "processed_rows": 0,
                "total_rows": 0,
                "progress_rate": 0.0,
                "last_case_id": "",
                "report_path": "",
                "message": str(exc),
            },
        )
        raise

    print(f"[OK] rows={report['rows_total']}")
    print(f"[OK] normalize_hit_rate={report['module_coverage']['normalize']['hit_rate']}")
    print(f"[OK] parse_field_hit_rate={report['module_coverage']['parse']['field_hit_rate']}")
    print(f"[OK] match_hit_rate={report['module_coverage']['match']['hit_rate']}")
    print(f"[OK] score_judgement_hit_rate={report['module_coverage']['score']['judgement_hit_rate']}")
    print(f"[OK] report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
