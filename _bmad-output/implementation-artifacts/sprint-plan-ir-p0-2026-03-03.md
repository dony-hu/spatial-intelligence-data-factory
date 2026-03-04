# Sprint Planning：IR-P0 收口冲刺计划（2026-03-03）

## 1. 冲刺目标

在本轮冲刺内完成 `IR-P0-01~IR-P0-04`，消除 Epic3 收口前置阻塞，达到“可复测、可会签、可追溯”的最小门槛。

## 2. 范围（In Scope）

1. `IR-P0-01`：可复现实验收 DB 基线
2. `IR-P0-02`：Epic3 核心验收测试重跑与报告固化
3. `IR-P0-03`：运行阶段枚举字典统一（API/UI/测试一致）
4. `IR-P0-04`：旧测试路径引用修正 + 证据索引映射表

## 3. 可执行顺序（重排后）

1. `IR-P0-01`（A-DEV）
2. `IR-P0-02`（A-QA）
3. `IR-P0-03`（A-ARC 主责，A-DEV 实施）
4. `IR-P0-04`（A-PM）

说明：`IR-P0-03/04` 必须在 `IR-P0-02` 完成并确认当前失败集后执行，避免基于旧口径修文档。

## 4. 任务卡（Owner + 验收 + 门禁）

### IR-P0-01

- Owner：A-DEV
- 交付物：
  - DB 基线初始化记录（`DATABASE_URL`、`alembic upgrade head`、smoke SQL）
  - 基线验证日志（可复跑）
- 验收标准：
  1. 业务关键表可查询（不再出现 `relation ... does not exist`）
  2. 迁移链路成功并可重复执行
- 门禁（Gate-1）：
  - 未通过时，禁止进入 `IR-P0-02`

### IR-P0-02

- Owner：A-QA
- 交付物：
  - Epic3 核心验收报告（JSON+MD）
  - 回归命令与结果摘要（含失败分类）
- 验收标准：
  1. 完成 pipeline/events/llm/rbac/upload-batch + Web E2E 的重跑
  2. 报告中明确阻断项与非阻断项
- 门禁（Gate-2）：
  - 未产出报告或报告不完整时，禁止进入 `IR-P0-03/04`

### IR-P0-03

- Owner：A-ARC（主）+ A-DEV（实装）
- 交付物：
  - 统一枚举字典清单（含 `dryrun_finished/publish_confirmed`）
  - API/UI/测试改动对齐记录
- 验收标准：
  1. API、UI、测试三处枚举一致
  2. 无 S2-14/S2-15 口径混用残留
- 门禁（Gate-3）：
  - 未完成枚举统一时，禁止最终会签

### IR-P0-04

- Owner：A-PM
- 交付物：
  - 文档旧测试路径修正提交
  - 证据索引映射表（测试文件 -> 验收报告 -> 工件路径）
- 验收标准：
  1. 文档中无失效测试路径
  2. 证据映射可支撑 BM Master 会签追溯
- 门禁（Gate-4）：
  - 未完成索引映射时，禁止最终会签

## 5. 冲刺完成定义（Sprint DoD）

1. `IR-P0-01~04` 全部完成并有证据路径。
2. Gate-1~Gate-4 全部通过。
3. Epic3 可进入最终会签流程（Go/No-Go 评估）。

## 6. 证据路径约定

1. 实施状态：`_bmad-output/implementation-artifacts/sprint-status.yaml`
2. 验收报告：`docs/acceptance/*.json` + `docs/acceptance/*.md`
3. 回归摘要：`output/test-reports/*.md`
4. 总控评审：`_bmad-output/implementation-artifacts/epic3-status-review-and-task-list-2026-03-02.md`
