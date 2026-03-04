# Story 4.1 - IR-P0-01 可复现实验收 DB 基线

Status: ready-for-dev

## 目标

建立可重复、可验证的验收数据库基线，确保后续 Epic3 验收测试运行在一致的 PG-only 环境上。

## 验收标准

1. 统一 `DATABASE_URL` 入口，所有验收脚本默认读取同一环境变量。
2. 执行 `alembic upgrade head` 后，关键业务表可通过 smoke SQL 查询。
3. 缺失或非法 `DATABASE_URL` 时显式失败（`blocked/error`），不允许 fallback。
4. 产出可复跑的基线初始化记录与验证日志。

## Tasks

- [ ] T1: 先补失败用例（TDD）
- [ ] T1.1: 新增 `DATABASE_URL` 缺失/非法时应 fail-fast 的失败用例
- [ ] T1.2: 新增 migration 后关键表存在性的失败用例
- [ ] T1.3: 新增 smoke SQL 失败语义测试（需返回明确错误）

- [ ] T2: 实现 DB 基线流程
- [ ] T2.1: 统一验收入口读取 `DATABASE_URL`
- [ ] T2.2: 接入 `alembic upgrade head` 与关键表 smoke SQL 校验
- [ ] T2.3: 异常路径统一为 `blocked/error`，禁止 fallback

- [ ] T3: 回归与证据固化
- [ ] T3.1: 执行回归并记录命令/结果
- [ ] T3.2: 输出基线初始化与验证记录到证据目录

## 测试命令（建议）

```bash
PYTHONPATH=. DATABASE_URL='postgresql://<user>:<pwd>@127.0.0.1:5432/<db>' .venv/bin/pytest -q \
  tests/test_mvp_acceptance_script.py \
  tests/test_observability_foundation_acceptance_script.py
```

## File List（预期）

- scripts/run_address_governance_mvp_acceptance.py
- scripts/run_observability_pg_foundation_acceptance.py
- services/governance_api/tests/test_migration_bootstrap_guard.py
- _bmad-output/implementation-artifacts/4-1-ir-p0-01-db-baseline-and-migration-smoke.md

## 证据路径

- output/acceptance/*.json
- output/acceptance/*.md
- output/test-reports/*.log

