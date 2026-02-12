from typing import Dict


class DDLTool:
    """DDL helper with mandatory dry-run validation."""

    FORBIDDEN_TOKENS = ("drop database", "truncate ")

    def generate(self, domain: str) -> Dict:
        table_name = f"dwd_{(domain or 'generic').replace('-', '_')}_result"
        sql = (
            f"CREATE TABLE IF NOT EXISTS {table_name} "
            "(task_id TEXT, status TEXT, updated_at TEXT);"
        )
        return {"sql": sql, "table_name": table_name}

    def dry_run(self, sql: str) -> Dict:
        norm = (sql or "").strip().lower()
        if not norm:
            return {"pass": False, "reason": "empty_sql"}

        for token in self.FORBIDDEN_TOKENS:
            if token in norm:
                return {"pass": False, "reason": f"forbidden_token:{token.strip()}"}

        if not norm.endswith(";"):
            return {"pass": False, "reason": "missing_semicolon"}

        if not norm.startswith(("create table", "alter table", "create index")):
            return {"pass": False, "reason": "unsupported_ddl"}

        return {"pass": True, "reason": "ok"}
