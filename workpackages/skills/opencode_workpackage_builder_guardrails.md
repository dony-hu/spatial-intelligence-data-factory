---
name: opencode_workpackage_builder_guardrails
version: v1.0.0
owner: factory-agent
scope: workpackage-build
---

# opencode 工作包构建护栏技能

## 目标
- 根据 nanobot 提供的规格，生成可执行工件，不改动运行时主程序代码。
- 保证输出工件可被治理 runtime 直接调用执行。

## 输入要求
1. 接收 nanobot 规格摘要（业务目标、I/O、API 计划、执行步骤）。
2. 接收工作包 ID 与版本。
3. 接收缺失依赖与 key 需求。

## 输出工件
1. `workpackage.json`
2. `scripts/run_pipeline.py`
3. `scripts/quality_checks.py`
4. `scripts/fetch_external_dependencies.py`（若存在 missing_apis）
5. `entrypoint.py`
6. `entrypoint.sh`
7. `README.md`
8. `config/provider_keys.env.example`（若存在 key 需求）

## 约束
1. 不允许生成 mock 数据路径。
2. 不允许 fallback 到本地伪能力。
3. 脚本失败必须返回真实错误并停止后续步骤。
4. 输出必须可观测：生成执行日志与结果摘要。

## 质量门禁
1. 工件路径齐全。
2. `workpackage.json` 字段完整且与 schema 对齐。
3. 运行脚本可启动且能输出 records/spatial_graph 结果结构。
