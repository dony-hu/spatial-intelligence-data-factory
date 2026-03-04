from __future__ import annotations

from pathlib import Path

from scripts.validate_evidence_index import build_evidence_index, validate_evidence_index_rows


def test_build_evidence_index_marks_missing_paths(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("引用 tests/not_exists_case.py\n", encoding="utf-8")
    rows = build_evidence_index([doc], repo_root=tmp_path)
    assert rows
    assert rows[0]["exists"] is False


def test_validate_evidence_index_requires_required_fields(tmp_path: Path) -> None:
    rows = [{"doc": "a.md"}]
    errors = validate_evidence_index_rows(rows, repo_root=tmp_path)
    assert any("missing field" in item for item in errors)


def test_validate_evidence_index_checks_path_existence(tmp_path: Path) -> None:
    keep = tmp_path / "exists.txt"
    keep.write_text("ok", encoding="utf-8")
    rows = [
        {
            "doc": "doc.md",
            "category": "artifact",
            "target_path": "exists.txt",
            "exists": True,
        },
        {
            "doc": "doc.md",
            "category": "artifact",
            "target_path": "missing.txt",
            "exists": False,
        },
    ]
    errors = validate_evidence_index_rows(rows, repo_root=tmp_path)
    assert any("missing.txt" in item for item in errors)
