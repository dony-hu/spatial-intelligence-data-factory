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

## 分步操作指南

### 操作前准备
- 保留 `archive/` 作为备份，**不删除**
- 每次操作后 Git 提交，便于回滚

---

### 第一步：迁移项目级文档（手动执行）
使用以下命令迁移项目级文档到 `.trae/documents/`：
```bash
# 迁移 PRD 和产品简介
cp archive/docs/prd-spatial-intelligence-data-factory-2026-02-10.md .trae/documents/
cp archive/docs/product-brief-spatial-intelligence-data-factory-2026-02-10.md .trae/documents/

# 迁移 kickoff 和 diagrams
cp -r archive/docs/kickoff .trae/documents/
cp -r archive/docs/diagrams .trae/documents/

# 迁移架构文档
cp archive/docs/architecture-alignment-spatial-intelligence-data-factory-2026-02-11.md .trae/documents/
cp archive/docs/architecture-design-data-cleaning-pipeline-v2.md .trae/documents/
cp archive/docs/architecture-enhancement-v2-2026-02-17.md .trae/documents/
cp archive/docs/pg-only-global-database-architecture-v1-2026-02-16.md .trae/documents/
```

---

### 第二步：合并技术设计文档（手动执行）
把技术设计文档复制到对应 change-id 的 tech-design.md：
```bash
# 合并到 address-governance-e2e-suite
cp archive/docs/address-governance-postgres-openhands-design-2026-02-14.md .trae/specs/address-governance-e2e-suite/
cp archive/docs/address-governance-postgres-openhands-implementation-plan-2026-02-14.md .trae/specs/address-governance-e2e-suite/
cp archive/docs/address-line-design-hypothesis-and-audit-cases-2026-02-14.md .trae/specs/address-governance-e2e-suite/

# 合并到 real-db-integration-and-dashboard
cp archive/docs/database-structure-design-and-validation-2026-02-16.md .trae/specs/real-db-integration-and-dashboard/

# 合并到 poi-shop-trust-verification
cp archive/docs/factory-closed-loop-address-verification-plan-2026-02-14.md .trae/specs/poi-shop-trust-verification/
```

---

### 第三步：合并可观测性与看板文档（手动执行）
```bash
# 合并到 observability-and-docs-improvement
cp archive/docs/address-line-observability-fields-2026-02-15.md .trae/specs/observability-and-docs-improvement/

# 合并到 observability-dashboard-enhancement
cp archive/docs/dashboard-data-contract.md .trae/specs/observability-dashboard-enhancement/
cp archive/docs/dashboard-refresh-contract.md .trae/specs/observability-dashboard-enhancement/
```

---

### 第四步：创建可信数据 HUB 的 change-id（手动执行）
```bash
# 创建 change-id 目录
mkdir -p .trae/specs/trust-data-hub-phase1/

# 复制文档
cp archive/docs/trust-data-hub-phase1-3-执行计划-2026-02-15.md .trae/specs/trust-data-hub-phase1/
cp archive/docs/trust-data-hub-v0.1-工作线启动说明.md .trae/specs/trust-data-hub-phase1/

# 参考现有 spec 创建 spec.md、tasks.md、checklist.md
```

---

### 第五步：Git 提交（每次操作后）
```bash
git add .trae/documents/ .trae/specs/
git commit -m "docs: 融合 archive 文档到 .trae/documents 和 .trae/specs"
```

---

## 下一步
1. 按上面的「分步操作指南」手动执行文档迁移
2. 每次操作后 Git 提交
3. 验证文档体系的一致性
