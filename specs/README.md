# 统一 Specs 基线（融合后）

## 1. 目的

将 `.trae/specs` 与当前主线 `docs/`（PRD/Epic/Architecture/Stories）融合为一套可追踪的规范基线，避免“双轨规格”继续分叉。

## 2. 规范来源

1. Trae 历史规格：
- `.trae/specs/*/spec.md`
- `.trae/specs/*/tasks.md`
- `.trae/specs/*/checklist.md`
- `.trae/documents/*`

2. 当前主线规格：
- `docs/prd-spatial-intelligence-data-factory-2026-02-27.md`
- `docs/epic-address-governance-mvp-2026-02-27.md`
- `docs/epic-observability-pg-unified-2026-02-27.md`
- `docs/architecture-*.md`
- `docs/stories/*.md`

## 3. 融合产物

1. 融合矩阵（人工可读）：  
`docs/specs-fusion-report-2026-02-27.md`

2. 融合状态（机器可读）：  
`docs/spec-fusion-status-2026-02-27.yaml`

## 4. 使用约束（从本次开始）

1. 新增/更新规格优先写入 `docs/` 主线文档，并同步更新融合状态 YAML。
2. `.trae/specs` 作为历史来源保留，不再作为唯一“当前事实”。
3. PRD 评审与架构评审统一引用融合矩阵与融合状态文件。
