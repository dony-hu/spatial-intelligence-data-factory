#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.process_expert_bootstrap import ProcessExpertBootstrapRunner
from tools.process_expert_llm_bridge import RealProcessExpertLLMBridge


def main() -> int:
    parser = argparse.ArgumentParser(description="Process Expert bootstrap runner (case-driven iterative drafting)")
    parser.add_argument(
        "--cases-file",
        default="testdata/fixtures/address-line-quality-audit-cases-2026-02-14.json",
        help="Case file path",
    )
    parser.add_argument("--output-dir", default="output/process_expert_bootstrap", help="Output directory")
    parser.add_argument("--max-rounds", type=int, default=3, help="Max iteration rounds")
    parser.add_argument("--min-rounds", type=int, default=1, help="Min iteration rounds before threshold stop")
    parser.add_argument("--score-threshold", type=float, default=0.82, help="Stop threshold")
    parser.add_argument("--continuous", action="store_true", help="Force continuous multi-round iteration")
    parser.add_argument("--continuous-rounds", type=int, default=5, help="Round count when --continuous is enabled")
    parser.add_argument("--llm-config", default="config/llm_api.json", help="LLM config path")
    parser.add_argument(
        "--trusted-sources-config",
        default="config/trusted_data_sources.json",
        help="Trusted data sources config path",
    )
    args = parser.parse_args()

    cases_file = (PROJECT_ROOT / args.cases_file).resolve() if not Path(args.cases_file).is_absolute() else Path(args.cases_file)
    output_dir = (PROJECT_ROOT / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    if not cases_file.exists():
        print(f"[ERROR] cases file not found: {cases_file}")
        return 2

    llm_config = (PROJECT_ROOT / args.llm_config).resolve() if not Path(args.llm_config).is_absolute() else Path(args.llm_config)
    bridge = RealProcessExpertLLMBridge(str(llm_config))
    print("[INFO] running in REAL LLM mode")

    trusted_sources_config = (
        (PROJECT_ROOT / args.trusted_sources_config).resolve()
        if not Path(args.trusted_sources_config).is_absolute()
        else Path(args.trusted_sources_config)
    )

    runner = ProcessExpertBootstrapRunner(
        llm_bridge=bridge,
        cases_file=cases_file,
        output_dir=output_dir,
        max_rounds=(max(2, args.continuous_rounds) if args.continuous else args.max_rounds),
        min_rounds=(max(2, args.continuous_rounds) if args.continuous else args.min_rounds),
        score_threshold=args.score_threshold,
        trusted_sources_config_path=trusted_sources_config,
    )
    result = runner.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
