#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.process_expert_llm_bridge import RealProcessExpertLLMBridge
from tools.process_expert_human_loop import ProcessExpertHumanLoopRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="Process Expert human+LLM semi-auto runner")
    parser.add_argument(
        "--requirement",
        default="请根据测试用例设计真实地址核实工艺草案，并由人工评审后决定是否修改与发布",
        help="Design requirement",
    )
    parser.add_argument("--process-code", default="", help="Optional process code")
    parser.add_argument("--process-name", default="", help="Optional process name")
    parser.add_argument("--domain", default="verification", help="Domain")
    parser.add_argument("--output-dir", default="output/process_expert_human_loop", help="Output directory")
    parser.add_argument("--decision-file", default="", help="Human decision JSON file (optional)")
    parser.add_argument("--llm-config", default="config/llm_api.json", help="LLM config path")
    args = parser.parse_args()

    output_dir = (PROJECT_ROOT / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)

    llm_config = (PROJECT_ROOT / args.llm_config).resolve() if not Path(args.llm_config).is_absolute() else Path(args.llm_config)
    bridge = RealProcessExpertLLMBridge(str(llm_config))
    print("[INFO] mode=human_llm_semi_auto")

    decision_payload = None
    if str(args.decision_file or "").strip():
        decision_file = (PROJECT_ROOT / args.decision_file).resolve() if not Path(args.decision_file).is_absolute() else Path(args.decision_file)
        if not decision_file.exists():
            print(f"[ERROR] decision file not found: {decision_file}")
            return 2
        decision_payload = json.loads(decision_file.read_text(encoding="utf-8"))

    runner = ProcessExpertHumanLoopRunner(
        llm_service=bridge,
        output_dir=output_dir,
    )
    artifacts = runner.run(
        requirement=str(args.requirement or "").strip(),
        process_code=str(args.process_code or "").strip(),
        process_name=str(args.process_name or "").strip(),
        domain=str(args.domain or "verification").strip(),
        decision_payload=decision_payload,
    )
    print(json.dumps(artifacts.summary, ensure_ascii=False, indent=2))
    print(f"[INFO] run_dir={artifacts.run_dir}")
    print("[INFO] 下一步：编辑 run_dir/human_decision_template.json 并通过 --decision-file 传入，执行人工决策后的增量修改。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
