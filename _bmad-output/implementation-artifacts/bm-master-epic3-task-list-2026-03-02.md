# BM Master 任务清单：Epic 3 统一推进（2026-03-02）

## 执行状态（更新：2026-03-02 12:45 +08:00）

1. `TASK-E3-001`：已完成
2. `TASK-E3-002`：已完成
3. `TASK-E3-003`：已完成
4. `TASK-E3-004`：已完成
5. `TASK-E3-005`：已完成

## 目标

修复 Epic 3 状态与证据不一致问题，完成可观测 Epic 的可审计收口，支撑统一推进与发布判断。

## Task 列表（可直接建单）

### TASK-E3-001（P0）补齐缺失 Story 工件

- Owner：BMM-Dev
- 范围：`3-1/3-2/3-3/3-4/3-14`
- 动作：
  1. 在 `_bmad-output/implementation-artifacts/` 新增对应 story 文件。
  2. 每个文件至少包含：`Status`、`Tasks`、`验收标准`、`测试命令`、`File List`、`证据路径`。
- DoD：
  1. 5 个 story 文件全部存在并可追踪。
  2. 每个 story 文件都能映射到对应测试与证据。
- 证据：
  - `_bmad-output/implementation-artifacts/3-*.md`

### TASK-E3-002（P0）统一状态口径（review/done）

- Owner：BMM-SM + BMM-PM
- 范围：`3-5~3-9` 与 `sprint-status.yaml`
- 动作：
  1. 将 Story 文档内 `Status` 与 Change Log 口径统一（禁止“正文 done，日志 review”）。
  2. 回写 `_bmad-output/implementation-artifacts/sprint-status.yaml`。
- DoD：
  1. Story 文件状态与 `sprint-status.yaml` 完全一致。
  2. 无冲突状态字段。
- 证据：
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
  - `_bmad-output/implementation-artifacts/3-5*.md` ... `3-9*.md`

### TASK-E3-003（P0）补齐 Full DoD 验收包（S2-5~S2-9）

- Owner：BMM-QA
- 范围：`S2-5/S2-6/S2-7/S2-8/S2-9`
- 动作：
  1. 为每个 Story 产出 `docs/acceptance/*.json + *.md`。
  2. 验收报告必须包含：测试命令、通过结果、No-Fallback 验证、剩余风险。
- DoD：
  1. S2-5~S2-9 全部具备双格式验收文件。
  2. 验收结论可独立支撑 Full DoD 判定。
- 证据：
  - `docs/acceptance/s2-5-*.json/.md` ... `s2-9-*.json/.md`

### TASK-E3-004（P1）运行态门禁一致性回归

- Owner：BMM-QA + BMM-Dev
- 动作：
  1. 执行 Epic 3 核心回归矩阵（API 契约、RBAC、UI E2E、No-Fallback）。
  2. 汇总单份 `epic-3-regression-summary` 报告。
- DoD：
  1. 失败用例有明确归因和阻断判断。
  2. 回归报告可被 BM Master 直接用于 Go/No-Go 会签。
- 证据：
  - `output/test-reports/epic-3-regression-summary-*.md`

### TASK-E3-005（P1）发布结论会签与 Epic 收口

- Owner：BM Master + BMM-Architect + BMM-QA
- 动作：
  1. 召开一次 Epic 3 收口会签（架构/质量/产品三方）。
  2. 若条件满足，将 `epic-3` 置为 `done`；否则保持 `in-progress` 并记录阻塞。
- DoD：
  1. 形成明确会签结论与时间戳。
  2. 状态变更有证据支撑且可回溯。
- 证据：
  - `docs/epic-runtime-observability-v2-review-*.md`（更新版）
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`

## 建议执行顺序（必须按序）

1. `TASK-E3-001`
2. `TASK-E3-002`
3. `TASK-E3-003`
4. `TASK-E3-004`
5. `TASK-E3-005`

## BM Master 每日检查点

1. P0 任务是否全部处于 `in-progress/done` 且有责任人。
2. 新增证据文件是否可打开、可对账、可复现。
3. `sprint-status.yaml` 是否与 story 文件状态一致。
