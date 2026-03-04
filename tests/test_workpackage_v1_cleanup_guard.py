from __future__ import annotations

from pathlib import Path


def test_legacy_workpackage_schema_removed() -> None:
    root = Path(__file__).resolve().parents[1]
    legacy_schema = root / "contracts" / "workpackage.schema.json"
    assert not legacy_schema.exists(), "旧版 contracts/workpackage.schema.json 应已清理"


def test_legacy_root_workpackages_removed() -> None:
    root = Path(__file__).resolve().parents[1]
    legacy_files = sorted((root / "workpackages").glob("wp-*.json"))
    assert not legacy_files, f"旧版 workpackages/wp-*.json 应已清理: {legacy_files}"


def test_scripts_no_legacy_schema_path_reference() -> None:
    root = Path(__file__).resolve().parents[1]
    old_ref = "contracts/workpackage.schema.json"
    offenders: list[str] = []
    for rel in [
        "scripts/run_p0_workpackage.py",
        "scripts/run_line_feedback_ci_block_demo.py",
    ]:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if old_ref in text:
            offenders.append(rel)
    assert not offenders, f"脚本仍引用旧 schema 路径: {offenders}"


def test_workpackage_schema_is_project_top_level() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "workpackage_schema" / "registry.json").exists(), "workpackage_schema 应位于项目一级目录"
    assert not (root / "contracts" / "workpackage_schema").exists(), "workpackage_schema 应已迁移"


def test_no_outdated_bundle_without_workpackage_json() -> None:
    root = Path(__file__).resolve().parents[1]
    bundles_root = root / "workpackages" / "bundles"
    if not bundles_root.exists():
        return
    outdated: list[str] = []
    for p in sorted(bundles_root.iterdir()):
        if not p.is_dir():
            continue
        if not (p / "workpackage.json").exists():
            outdated.append(p.name)
    assert not outdated, f"过时 bundle（缺少 workpackage.json）应已清理: {outdated}"


def test_architecture_doc_mentions_workpackage_schema_and_contracts_usage() -> None:
    root = Path(__file__).resolve().parents[1]
    architecture_doc = root / "docs" / "architecture-spatial-intelligence-data-factory-2026-02-28.md"
    assert architecture_doc.exists(), "架构文档缺失"
    text = architecture_doc.read_text(encoding="utf-8")
    assert "/workpackage_schema" in text, "架构文档应声明 workpackage_schema 为项目一级目录"
    assert "contracts/" in text, "架构文档应说明 workpackage_schema 对 contracts 的使用关系"
