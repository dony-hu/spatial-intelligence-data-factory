from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def test_runnable_workpackage_bundle_example_can_execute_end_to_end(tmp_path) -> None:
    root = Path(__file__).resolve().parents[1]
    bundle_dir = root / "workpackages" / "bundles" / "address-governance-runtime-demo-v1.0.0"
    assert bundle_dir.exists(), "示例工作包目录缺失"

    required_files = [
        "workpackage.json",
        "entrypoint.py",
        "entrypoint.sh",
        "scripts/run_pipeline.py",
        "observability/line_observe.py",
        "input/sample_addresses_10.csv",
        "config/provider_keys.env.example",
    ]
    for rel in required_files:
        assert (bundle_dir / rel).exists(), f"缺失文件: {rel}"

    output_dir = tmp_path / "runtime_output"
    env = os.environ.copy()
    env["OUTPUT_DIR"] = str(output_dir)
    env["INPUT_CSV"] = str(bundle_dir / "input" / "sample_addresses_10.csv")

    proc = subprocess.run(
        ["python3", "entrypoint.py"],
        cwd=str(bundle_dir),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    output_json = output_dir / "runtime_output.json"
    assert output_json.exists(), "未生成 runtime_output.json"
    payload = json.loads(output_json.read_text(encoding="utf-8"))

    assert isinstance(payload.get("records"), list)
    assert len(payload["records"]) >= 10
    assert isinstance(payload.get("spatial_graph"), dict)
    graph = payload["spatial_graph"]
    for field in ["nodes", "edges", "metrics", "failed_row_refs", "build_status"]:
        assert field in graph
