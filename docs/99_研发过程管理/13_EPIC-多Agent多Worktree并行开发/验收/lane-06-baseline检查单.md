# lane-06 baseline 检查单

## 1. 结论口径

- 当前结论：`PASS`
- 含义：本轮 Epic13 按文档治理主题收口，`lane-06` 只要求形成 baseline 文档、统一验证入口和 gate 口径；完整 smoke 与本地 `.venv` 就绪属于后续真实业务开发阶段的 follow-up，不再作为本轮收尾门禁。

## 2. 检查项

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 是否形成统一验证入口文档 | `PASS` | 已形成 `测试/lane-06-baseline与统一验证入口.md`。 |
| 是否区分 P0 / P1 / P2 验证层级 | `PASS` | 已区分仓库卫生、核心回归、扩展回归。 |
| 是否给出统一 gate 结论口径 | `PASS` | 已定义 `PASS / BLOCKED / NEEDS-FIX`。 |
| 是否至少执行一轮真实轻量探测 | `PASS` | 已执行 `./scripts/check_repo_hygiene.sh` 与 `./scripts/check_workpackage_cleanup.sh`。 |
| 仓库卫生检查是否通过 | `PASS` | 当前无 tracked `.venv` 和 local-file-db 主线路径引用。 |
| worktree 本地 `.venv` 是否已就绪 | `FOLLOW-UP` | 当前 `codex/lane-06-qa-integration` 下不存在 `.venv/bin/python`，但这不阻塞本轮文档治理收口。 |
| 工作包清理守卫是否通过 | `FOLLOW-UP` | 当前失败于 `pytest: command not found`，保留给后续真实测试环境初始化阶段处理。 |
| 最小真实链路与 Web E2E 是否已具备运行前提 | `FOLLOW-UP` | 命令已确认存在，但依赖 PostgreSQL、LLM、Playwright 等环境。 |

## 3. 当前 follow-up

1. `codex/lane-06-qa-integration` worktree 尚未初始化本地 `.venv`。
2. `check_workpackage_cleanup.sh` 依赖 `pytest`，当前 worktree 直接报 `pytest: command not found`。
3. 最小真实链路和 Web E2E 仍依赖 PostgreSQL、LLM 配置和 Playwright Chromium。
4. 外部 TEA skill 与 Linear 绑定仍是 Epic 级后续项。

## 4. 建议后续动作

1. 在 `codex/lane-06-qa-integration` worktree 内初始化本地 `.venv` 并安装测试依赖。
2. 重跑 `./scripts/check_workpackage_cleanup.sh`，把结果写回本检查单。
3. 环境就绪后按 baseline 顺序继续执行 Runtime 核心契约回归、最小真实链路和 Web E2E 最小入口。
4. 让 `PAR-S5` 直接复用这里的 gate 口径和 Lane 进入集成窗口前必填字段。
