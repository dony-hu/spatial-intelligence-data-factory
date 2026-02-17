# Tasks

## Phase 1: P0 - 立即行动（高优先级）

- [x] Task 1: 修复 .gitignore - 添加 `.venv/` 忽略规则
  - [x] 读取当前 `.gitignore`
  - [x] 添加 `.venv/` 规则
  - [x] 从 Git 中移除已跟踪的 `.venv/`（如果存在）

- [x] Task 2: 实现看板自动化 - E2E 测试通过后自动更新看板
  - [x] 分析当前 E2E 测试执行流程
  - [x] 设计集成方案（修改测试脚本或新增 wrapper）
  - [x] 实现测试通过后调用 `collect_governance_metrics.py`
  - [x] 验证集成效果

## Phase 2: P1 - 短期（中优先级）

- [x] Task 3: 文档规范化 - 批量替换硬编码绝对路径
  - [x] 扫描所有文档文件，识别硬编码路径
  - [x] 设计替换规则（绝对路径 → 相对路径）
  - [x] 批量执行替换
  - [x] 验证关键文档的可访问性

## Phase 3: P2 - 中期（可选）

- [ ] Task 4: 统一配置管理（可选）
  - [ ] 引入 pydantic-settings
  - [ ] 重构配置加载逻辑
  - [ ] 更新相关文档

# Task Dependencies
- Task 2 依赖 Task 1 完成（确保环境清洁）
- Task 3 可以与 Task 1-2 并行执行
- Task 4 可选，不依赖其他任务
