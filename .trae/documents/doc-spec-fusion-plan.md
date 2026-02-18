# 文档与规范融合计划

## 目标
将 `archive/docs/` 和 `archive/specs/` 中的内容融合到当前的 `.trae/specs/` 和 `.trae/documents/` 文档体系中，保持一致性和可追溯性。

---

## 当前文档体系

### .trae/specs/（规范目录）
按照 change-id 组织的规范，每个 change-id 包含：
- `spec.md` - 需求规范
- `tasks.md` - 任务列表
- `checklist.md` - 验收检查点
- `tech-design.md` - 技术设计（可选）
- `test-design.md` - 测试设计（可选）

现有的 specs：
- `address-governance-e2e-suite/`
- `observability-and-docs-improvement/`
- `observability-dashboard-enhancement/`
- `poi-shop-trust-verification/`
- `real-db-integration-and-dashboard/`
- `system-status-planning/`
- `workpackage-structure-design/`

### .trae/documents/（文档目录）
存放项目级别的文档，非 change-id 特定的。

现有的 documents：
- `智能体架构增强实施计划.md`

---

## Archive 内容分类

### A. 项目级文档（移到 .trae/documents/）
| 原路径 | 目标路径 |
|---|---|
| `archive/docs/prd-spatial-intelligence-data-factory-2026-02-10.md` | `.trae/documents/prd-spatial-intelligence-data-factory-2026-02-10.md` |
| `archive/docs/product-brief-spatial-intelligence-data-factory-2026-02-10.md` | `.trae/documents/product-brief-spatial-intelligence-data-factory-2026-02-10.md` |
| `archive/docs/kickoff/` | `.trae/documents/kickoff/` |
| `archive/docs/diagrams/` | `.trae/documents/diagrams/` |
| `archive/docs/architecture-alignment-spatial-intelligence-data-factory-2026-02-11.md` | `.trae/documents/architecture-alignment-spatial-intelligence-data-factory-2026-02-11.md` |
| `archive/docs/architecture-design-data-cleaning-pipeline-v2.md` | `.trae/documents/architecture-design-data-cleaning-pipeline-v2.md` |
| `archive/docs/architecture-enhancement-v2-2026-02-17.md` | `.trae/documents/architecture-enhancement-v2-2026-02-17.md` |
| `archive/docs/pg-only-global-database-architecture-v1-2026-02-16.md` | `.trae/documents/pg-only-global-database-architecture-v1-2026-02-16.md` |

### B. Story/Feature 文档（合并到对应的 .trae/specs/ 或创建新的 change-id）
| 原路径 | 处理方式 |
|---|---|
| `archive/docs/stories/` | 拆分成独立的 change-id，放到 `.trae/specs/` 下 |
| `archive/docs/STORY-*.md` | 合并到对应的 change-id 或创建新的 |

### C. 技术设计文档（合并到对应 change-id 的 tech-design.md）
| 原路径 | 目标 change-id |
|---|---|
| `archive/docs/address-governance-postgres-openhands-design-2026-02-14.md` | `address-governance-e2e-suite/` |
| `archive/docs/address-governance-postgres-openhands-implementation-plan-2026-02-14.md` | `address-governance-e2e-suite/` |
| `archive/docs/address-line-design-hypothesis-and-audit-cases-2026-02-14.md` | `address-governance-e2e-suite/` |
| `archive/docs/database-structure-design-and-validation-2026-02-16.md` | `real-db-integration-and-dashboard/` |

### D. 可观测性与看板文档（合并到对应 change-id）
| 原路径 | 目标 change-id |
|---|---|
| `archive/docs/address-line-observability-fields-2026-02-15.md` | `observability-and-docs-improvement/` |
| `archive/docs/dashboard-data-contract.md` | `observability-dashboard-enhancement/` |
| `archive/docs/dashboard-refresh-contract.md` | `observability-dashboard-enhancement/` |
| `archive/docs/factory-closed-loop-address-verification-plan-2026-02-14.md` | `poi-shop-trust-verification/` |

### E. 可信数据 HUB 文档（创建新的 change-id）
| 原路径 | 目标 change-id |
|---|---|
| `archive/docs/trust-data-hub-phase1-3-执行计划-2026-02-15.md` | 创建 `trust-data-hub-phase1/` |
| `archive/docs/trust-data-hub-v0.1-工作线启动说明.md` | 创建 `trust-data-hub-phase1/` |

### F. 周报与验收报告（不需要了，跳过）
**说明**: 周报和验收报告不需要了，保留在 archive/ 中即可，不做迁移。

---

## Archive/specs/ 处理
| 原路径 | 目标 |
|---|---|
| `archive/specs/001-system-design-spec/` | 合并到现有 specs 或创建新的 `system-design/` |

---

## 融合原则
1. **保持可追溯性**：保留原文件名，便于查找历史
2. **按 change-id 组织**：Story/Feature 级文档必须放在对应 change-id 下
3. **项目级文档在 .trae/documents/**：PRD、产品简介、架构文档等
4. **不删除 archive/**：保留作为备份，后续可清理

---

## 下一步
1. 确认融合方案
2. 逐步执行文档迁移
