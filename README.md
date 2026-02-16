# 数据工厂项目（Data Factory Project）

本仓库用于承载数据工厂项目的项目规范、治理规则、执行日志与测试数据管理机制，服务于多人、多 AI、多工具协作下的数据平台建设与持续交付。
平台定位不变：持续服务上海、昆山、吴江、北京、深圳宝安等多地业务场景的交付与运营。

## 项目背景

在企业数字化与智能化转型过程中，数据已成为核心资产。现有数据建设面临以下共性问题：

- 数据孤岛与重复开发并存，采集/清洗/计算逻辑复用不足。
- 数据质量不可控，缺乏统一、自动化的检测与反馈机制。
- 数据流程可追踪性不足，问题定位与责任归属困难。
- 实时与批处理任务协同能力弱，难以支撑准实时业务需求。
- 数据交付稳定性不足，影响分析质量与决策效率。

组织已具备数据湖/数仓、基础 ETL 和初步治理能力，但缺少覆盖全流程的统一执行与交付体系，因此需要建设数据工厂平台。

## 项目目标

核心目标：建立可复用、可治理、可监控、可扩展的数据工厂平台，支撑全组织数据自动化生产与消费。

具体目标：

1. 标准化数据生产：统一采集、清洗、转换框架，支持批流一体任务模型。
2. 可控的数据质量：提供规则校验、统计校验与异常检测能力。
3. 全流程可追踪与可审计：支持血缘、执行日志、指标变更与运行快照查询。
4. 提升开发效率与交付质量：提供统一组件、模板、CI/CD 与版本回滚机制。
5. 支撑实时数据能力：打通消息队列与流计算引擎，统一调度与监控。
6. 增强数据消费能力：通过数据 API 服务 BI、模型训练与报告系统。

## 执行内核升级（Agent）

在不改变多地业务场景与交付目标的前提下，项目新增 Agent 驱动执行内核，用于提升自动化、可审计性与持续演进能力。

### Agent 判定标准

一个模块被定义为 Agent，至少满足：

1. 目标驱动（Goal-Oriented）
2. 自主决策循环（Reasoning Loop）
3. 动态工具调度（Tool Autonomy）
4. 状态与记忆管理（State and Memory）

### Agent 角色体系（平台层）

- 需求理解 Agent：解析业务目标与指标体系
- 数据探索 Agent：Profiling 与结构推断
- 建模 Agent：生成逻辑/物理模型
- 质量 Agent：质量规则与监控
- 编排 Agent：DAG 与调度生成
- 影响分析 Agent：血缘与依赖分析
- 执行 Agent：自动落地实施
- 审计 Agent：合规与留痕
- 推理服务 Agent：推理服务生成与部署

### 自动化与人工边界

- 高自动化环节：Profiling、建模草案、ETL/DAG、预标注、推理部署、质量监控
- 必须人工审批：指标口径、权限合规、生产发布、标签体系、SLA 策略

### 数据底座原则

Lakehouse 负责生长与试错，DW 负责权威输出与治理审计。

## 核心业务场景

1. 地址治理：标准化、分词、纠错、地址结构化。
2. 地址与空间实体关联：以及公安、城市治理等业务数据与空间实体映射。
3. 数据标注与质检：自动化预标注、人工标注、抽检与复核闭环。
4. 文档与模型抽取：从 PDF、Word、BIM 中提取空间实体属性、坐标与结构信息。
5. 互联网内容融合：抓取公开信息并与空间实体关联融合。
6. 实体发现与运营闭环：当入库数据引用实体不存在时，触发多源核验、人工确认与现场核实任务。

## 关键里程碑

1. `0-2 个月`：启动与基础能力搭建  
产出：架构白皮书、基础可运行版本、初始监控看板。
2. `2-4 个月`：核心模块与流程规范化  
产出：组件库、任务模板、SQL/任务规范指南。
3. `4-6 个月`：可视化开发与自助分析  
产出：可视化编排工具、元数据查询中心、API 服务。
4. `6-9 个月`：全面上线与优化  
产出：全链路 SLA 报表、运维 SOP、治理手册。

## 预期价值

- 降低数据开发与维护成本，提升组件复用率。
- 提升数据质量与稳定性，减少下游返工。
- 缩短数据交付周期，提升业务响应速度。
- 增强数据资产可治理、可追踪、可度量能力。
- 支撑 BI 与 AI 场景，提升决策质量与业务增长能力。

## 成功衡量标准（KPI）

| KPI 项目 | 目标 |
| --- | --- |
| 数据任务开发周期 | 比现状提升 `>= 50%` |
| 数据质量自动检测覆盖率 | `>= 90%` |
| 数据任务失败自动恢复率 | `>= 95%` |
| 数据血缘完整率 | `>= 98%` |
| 实时数据延迟 | `<= 30s` |
| 未识别实体自动发现召回率 | `>= 90%` |
| 自动核验后无需人工比例 | `>= 60%`（阶段目标） |
| 人工审核准确率 | `>= 95%` |
| 现场核实任务按时完成率 | `>= 90%` |
| 误创建/误合并率 | `<= 1%` |

## 仓库结构

- `PROJECT_REQUIREMENTS.md`：项目级通用要求（MUST/SHOULD/MAY）。
- `PROJECT_MANAGEMENT_REQUIREMENTS.md`：项目管理、日志与治理规则。
- `TOOLING_ADAPTERS.md`：不同 AI/IDE 工具的适配规范。
- `AGENTS.md`：仓库级代理规则（含文档中文强制策略）。
- `logs/`：项目每日、成员每日、团队周/月报。
- `templates/`：日志与汇报模板。
- `schemas/`：日志结构校验 Schema。
- `testdata/`：测试数据目录、清单、样例与约束。
- `scripts/testdata/`：测试数据拉取与校验脚本。
- `docs/`：专题治理文档（如测试数据治理）。

## 快速开始（测试数据）

```bash
scripts/testdata/pull.sh geo_poi_smoke_p0
scripts/testdata/verify.sh geo_poi_smoke_p0
```

更多说明见：

- `testdata/README.md`
- `docs/testdata-governance.md`
- `docs/entity-operations-closed-loop.md`
- `docs/test-case-matrix.md`
- `docs/architecture-alignment-spatial-intelligence-data-factory-2026-02-11.md`（含云上建设、专网迁移与 Qwen/GLM/腾讯混元适配选型）
- `docs/cloud-bootstrap-runbook.md`（云上环境搭建执行手册）

## Story 落地运行入口（2026-02）

### 一键拉起三面板（工厂+两条产线）

```bash
/Users/huda/Code/worktrees/integration/scripts/panel_up_all.sh
```

默认地址：
- 工厂工艺专家对话室：`http://127.0.0.1:8877`
- 公安地址产线面板：`http://127.0.0.1:8787`
- 城市治理产线面板：`http://127.0.0.1:8788`

### 工厂脚本

- `scripts/run_story.sh`：发布模板并启动工艺专家对话室（前台）
- `scripts/clean_data.sh`：清理工厂测试/调试数据
- `scripts/panel_up.sh`：后台拉起工艺专家对话室

更多见：`docs/STORY-runtime-scripts.md` 与 `docs/STORY-alignment-check-2026-02-14.md`。

## P0 核心引擎工作包执行

P0 工作包：`workpackages/wp-core-engine-p0-stabilization-v0.1.0.json`

本地执行（建议 Python 3.11+）：

```bash
python scripts/run_p0_workpackage.py
```

执行产物：

- `output/workpackages/wp-core-engine-p0-stabilization-v0.1.0.report.json`
- `output/workpackages/line_feedback.latest.json`
