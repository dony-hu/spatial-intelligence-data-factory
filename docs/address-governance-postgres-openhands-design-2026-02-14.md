# 地址治理目标态架构设计（Postgres + FastAPI/Pydantic + OpenHands）

## 1. 目标与边界

### 1.1 总目标（面向完备功能）
- 建立可持续演进的地址治理工厂：支持批处理、准实时、人工复核、规则治理、证据审计、质量运营与跨场景复用。
- 数据层统一迁移至 PostgreSQL，形成可回放、可审计、可扩展的数据底座。
- 执行层统一采用 OpenHands，替换现有直连 LLM 调用链，并支持后续主流 Coding Agent skills 复用。
- API 层统一采用 FastAPI + Pydantic + JSON Schema，实现强约束输入输出与契约化演进。
- 在满足近期交付的同时，预留二/三期能力：流程编排、在线服务化、质量自优化、组织级治理。

### 1.2 近期目标（阶段一）
- 跑通“提交任务 -> 异步治理 -> 结果查询 -> 人工复核 -> 规则回灌”闭环。
- 完成最小能力：标准化、解析、匹配、去重、置信度分层。
- 形成可演进的模块边界，避免一次性重构。

### 1.3 当前非目标（阶段一）
- 不追求全自动“零人工”治理，保留人工复核门禁。
- 不在一期引入复杂图编排框架作为强依赖（如 LangGraph 可后置为可插拔增强）。
- 不在一期实现完整前端系统，仅提供 API 与最小复核入口能力。

## 2. 目标态总体架构

```
Client / Console
   -> governance-api (FastAPI)
  -> policy & schema gateway
      -> PostgreSQL (task / raw / canonical / review / ruleset / audit)
      -> Redis (queue)
      -> governance-worker (RQ)
          -> address_core (normalize/parse/match/score)
          -> AgentRuntimeAdapter
               -> OpenHandsRuntime (主)
  -> observability (metrics/logs/traces)
  -> ops console / reporting
```

### 2.1 职责边界
- `governance-api`
  - 任务提交、状态查询、结果查询、人工复核、规则配置。
  - 入参/出参的 Pydantic 校验。
  - 幂等校验（idempotency_key）与权限审计。
- `governance-worker`
  - 执行地址治理 pipeline。
  - 调用 OpenHands 执行策略与工具。
  - 输出 `canonical + confidence + evidence + strategy`。
- `OpenHandsRuntime`
  - 负责 Agent 推理与工具调度。
  - 不直接写业务库，仅通过 worker 返回结构化执行结果。

### 2.2 目标态能力分层
- `接口层`：任务提交、结果查询、复核操作、规则治理、权限与审计。
- `编排层`：任务生命周期、重试补偿、状态流转、SLA 管控。
- `执行层`：规则执行、OpenHands 策略决策、工具技能调用。
- `数据层`：标准化实体、证据链、规则版本、运行指标、审计日志。
- `运营层`：质量看板、问题聚类、规则迭代建议、发布灰度与回滚。

## 3. OpenHands 接入设计

## 3.1 接入原则
- 控制面（API）与执行面（Agent）解耦。
- 以统一适配器收口，禁止业务代码直接耦合 OpenHands SDK 细节。
- 执行结果必须可审计（prompt/tool/result/run_id）。

### 3.2 适配器接口（建议）

```python
class AgentRuntimeAdapter(Protocol):
    def run_task(self, task_context: dict, ruleset: dict) -> dict:
        """返回结构化结果：
        {
          "strategy": "rule_only|match_dict|match_poi|human_required",
          "canonical": {...},
          "confidence": 0.0,
          "evidence": {...},
          "actions": [...],
          "agent_run_id": "..."
        }
        """
```

### 3.3 回退策略
- 环境变量开关：`AGENT_RUNTIME=openhands`（默认）
- 紧急回退：`AGENT_RUNTIME=legacy`（仅故障兜底，不作为常态双栈）

## 4. 数据模型（PostgreSQL）

## 4.1 核心表
- `addr_batch`：批次元信息。
- `addr_raw`：原始地址输入与基础字段。
- `addr_canonical`：标准化结果、策略、证据与规则版本。
- `addr_review`：人工复核决策与改写结果。
- `addr_ruleset`：规则配置版本。
- `addr_task_run`：任务状态、重试与执行审计。
- `api_audit_log`：控制面 API 调用留痕。

### 4.2 扩展与索引
- 启用 `pg_trgm`：支持地址文本相似检索。
- `addr_raw.raw_text` / `addr_canonical.canon_text`：GIN(trgm) 索引。
- `addr_raw.hash`：BTree 索引用于 exact 去重。

## 5. API 设计（阶段化）

### 5.1 任务与结果
- `POST /v1/governance/tasks`：提交治理任务（异步）。
- `GET /v1/governance/tasks/{task_id}`：查询任务状态。
- `GET /v1/governance/tasks/{task_id}/result`：获取治理结果与证据摘要。

### 5.2 人工复核
- `POST /v1/governance/reviews/{task_id}/decision`
  - `approved/rejected/edited`
  - 支持 `final_canon_text` 与 `comment`。

### 5.3 规则管理
- `GET /v1/governance/rulesets/{ruleset_id}`
- `PUT /v1/governance/rulesets/{ruleset_id}`（草稿）
- `POST /v1/governance/rulesets/{ruleset_id}/publish`（发布）

### 5.4 目标态扩展接口（二/三期）
- `POST /v1/governance/tasks/{task_id}/replay`：按规则版本回放。
- `GET /v1/governance/quality/metrics`：质量运营指标。
- `POST /v1/governance/rulesets/{ruleset_id}/gray-release`：规则灰度发布。
- `POST /v1/governance/skills/{skill_id}/bind`：技能注册与权限绑定。

## 6. 能力建设路线（从阶段一到目标态）

### 6.0 阶段一（可交付基线）
- Normalization/Parsing/Matching/Dedup/Confidence 分层。
- 人工复核闭环、证据落库、规则版本化。

### 6.1 阶段二（规模化治理）
- 多源候选融合（字典 + 外部服务 + 历史样本）。
- 批次并行优化、任务优先级、失败自动补偿。
- 质量评估体系：复核通过率、稳定性、时延、误判类型画像。

### 6.2 阶段三（完备能力）
- 在线治理（准实时）与离线治理协同。
- 规则与策略自动推荐（人工确认后应用）。
- 技能库接入与跨场景复用（地址、网点、场景图谱等）。
- 可插拔高级编排（必要时引入 LangGraph/状态图引擎）。

### 6.1 Normalization
- 全半角统一、空白/标点清洗、别名映射、数字表达归一。

### 6.2 Parsing
- 规则拆分：省市区/街道路名/门牌/楼栋单元房号。
- 解析失败输出 partial 结果，不抛弃记录。

### 6.3 Matching
- 字典召回 + `pg_trgm` 相似度 topK。
- 轻量打分函数：字段一致性 + 文本相似 + 规则命中。

### 6.4 Dedup
- exact 去重（hash）
- 轻量 fuzzy（同城同街 + 相似阈值）

### 6.5 Confidence 分层
- `>= T_high`：自动通过。
- `T_low ~ T_high`：建议人工。
- `< T_low`：强制人工。

## 7. 校验与合规

### 7.1 输入校验
- Pydantic 类型与格式校验。
- JSON Schema 业务规则校验（必填、长度、枚举、字段关系）。

### 7.2 审计
- 每次任务执行保留 `ruleset_version`、`agent_run_id`、`evidence`。
- 保留复核与规则发布记录，支持回放与问责。

## 8. 治理与可靠性基线
- 幂等：所有写接口必须支持 `idempotency_key`。
- 可追踪：核心流程必须携带 `trace_id/task_id/agent_run_id`。
- 可回放：规则版本、输入快照、执行证据完整留存。
- 可回滚：规则和执行策略支持灰度与一键回退。
- 安全合规：敏感字段脱敏、最小权限、操作审计不可篡改。

## 9. 风险与缓解
- OpenHands 接入初期稳定性风险：通过运行时开关与重试/超时控制降低影响。
- 地址脏数据导致误判：通过分层 confidence + 强制人工复核兜底。
- 规则频繁变更带来回归风险：规则版本化 + 小流量灰度发布。

## 10. 后续演进（二期/三期）
- 评估引入 LangGraph 管理多阶段状态机（Profile/Diagnose/Propose/Run/Evaluate/Decide）。
- 引入更细粒度技能权限模型与主流 Coding Agent skills 复用机制。
