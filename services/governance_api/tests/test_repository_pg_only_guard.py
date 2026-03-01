from __future__ import annotations

import importlib

import pytest


def test_repository_rejects_non_pg_url_when_non_pg_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@localhost/governance")

    with pytest.raises(RuntimeError, match="postgresql://"):
        mod = importlib.import_module("services.governance_api.app.repositories.governance_repository")
        importlib.reload(mod)
