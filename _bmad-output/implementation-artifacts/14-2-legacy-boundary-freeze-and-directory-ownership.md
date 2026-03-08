# Story 14.2 - legacy 边界冻结与目录归属声明

Status: ready-for-dev

## 目标

冻结 `src/` 与目标目录的归属边界，防止后续新增能力继续落到 legacy 壳层。

## 验收标准

1. `src/` 被明确声明为 legacy/compat 过渡面。
2. 新增正式能力默认落点已明确。
3. 首轮 owned surface 与禁止跨界范围已形成可执行说明。
4. 目录迁移、契约迁移、实现迁移三者拆分规则已明确。

## Tasks

- [ ] T1: 明确 legacy 与 target 目录归属
- [ ] T2: 补充 owned surface 与禁止跨界范围
- [ ] T3: 回填工程规范或过程文档

## File List（预期）

- docs/99_研发过程管理/14_EPIC-重构实施基线落位/故事/EPIC4-S2-legacy边界冻结与目录归属声明.md

