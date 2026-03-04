from __future__ import annotations

import json
from pathlib import Path


def test_workpackage_schema_has_versioned_companion_templates() -> None:
    root = Path(__file__).resolve().parents[1]
    base = root / "workpackage_schema"
    registry_path = base / "registry.json"
    assert registry_path.exists(), "registry.json 缺失"

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    v1 = (registry.get("versions") or {}).get("v1") or {}
    companion = v1.get("companion_artifacts") or {}
    assert companion.get("readme_template") == "templates/v1/workpackage_bundle.README.v1.md"
    assert companion.get("bundle_structure_template") == "templates/v1/workpackage_bundle.structure.v1.md"

    readme_template_path = base / str(companion.get("readme_template") or "")
    bundle_tree_template_path = base / str(companion.get("bundle_structure_template") or "")
    assert readme_template_path.exists(), "README 模版缺失"
    assert bundle_tree_template_path.exists(), "结构模版缺失"


def test_workpackage_schema_registry_paths_cover_version_directories() -> None:
    root = Path(__file__).resolve().parents[1]
    base = root / "workpackage_schema"
    registry = json.loads((base / "registry.json").read_text(encoding="utf-8"))
    versions = registry.get("versions") or {}
    assert isinstance(versions, dict) and versions
    for ver, meta in versions.items():
        schema_file = str((meta or {}).get("schema_file") or "")
        assert schema_file.startswith(f"schemas/{ver}/"), f"{ver} schema 目录不匹配"
        assert (base / schema_file).exists(), f"{ver} schema 文件缺失"
        for sample in (meta or {}).get("examples") or []:
            sample_path = str(sample or "")
            assert sample_path.startswith(f"examples/{ver}/"), f"{ver} example 目录不匹配"
            assert (base / sample_path).exists(), f"{ver} example 文件缺失"
