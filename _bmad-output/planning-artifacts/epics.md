# Epic 14：重构实施基线落位

## Epic Goal

为全面重构建立可执行实施基线，先冻结共享契约、legacy 边界、结构拆分切口和测试 baseline，再允许后续多 Lane 真实实施。

## Story 14-1：共享契约冻结与消费基线固化

作为 `lane-03` 契约 owner，
我希望在首轮重构实施前冻结共享契约并明确唯一消费口径，
以便 Factory Agent、Runtime / API 与测试基线不会在过渡态中各自猜测接口。

### Acceptance Criteria

1. 形成首版共享契约冻结清单。
2. 每个共享契约对象都有唯一 owner 或串行变更路径。
3. 明确下游 Lane 的消费基线和禁止自行推导的边界。
4. 契约 PR 与实现 PR 的拆分规则明确。
5. 输出仅修改文档与契约说明，不直接混入业务实现迁移。

## Story 14-2：legacy 边界冻结与目录归属声明

作为规划 / 集成编排 owner，
我希望冻结 `src/` 与目标目录的归属边界，
以便后续新增能力不再继续落到 legacy 壳层里。

### Acceptance Criteria

1. `src/` 被明确声明为 legacy/compat 过渡面。
2. 新增正式能力默认落点已明确。
3. 首轮 owned surface 与禁止跨界范围已形成可执行说明。
4. 目录迁移、契约迁移、实现迁移三者的拆分规则已明确。

## Story 14-3：Factory Agent 巨石拆分但保持外部契约不变

作为 `lane-01` owner，
我希望拆分 `packages/factory_agent/` 的内部结构，
以便后续框架替换和模块演进有稳定落点，同时不打破现有外部契约。

### Acceptance Criteria

1. façade、conversation、blueprint、trace、memory、publish/dryrun 协调逻辑的切分方案明确。
2. 外部正式契约保持不变。
3. 结构拆分切口可用最小测试集验证。
4. 不在本 Story 中夹带框架整体替换。

## Story 14-4：Runtime / API seam 收敛与主链边界清理

作为 `lane-02` owner，
我希望收敛 `services/governance_api/` 与 `services/governance_worker/` 的 seam，
以便主链运行边界清晰、测试口径稳定，并为后续控制层替换留出安全切口。

### Acceptance Criteria

1. Runtime / API 的首轮 seam 收敛范围明确。
2. 主链边界清理不破坏现有 `workpackage executor` 执行面。
3. Router、service、worker 边界拆分切口可验证。
4. 不在本 Story 中夹带控制层整体语言替换。

## Story 14-5：旧测试口径清理与 baseline 建立

作为 `lane-06` owner，
我希望清理仍绑定旧链路的测试口径并建立 EPIC4 baseline，
以便后续结构拆分时能够区分“旧 seam 问题”和“现行主链问题”。

### Acceptance Criteria

1. 形成 smoke baseline。
2. 形成 known-fail 清单。
3. 建立统一验证入口。
4. 明确哪些失败属于旧 seam，哪些属于主链真实回归。

## Story 14-6：集成回归与首轮并行开发准入

作为集成值班位与 QA owner，
我希望在 `S3 / S4 / S5` 收口后给出首轮并行开发准入结论，
以便后续各 Lane 能按统一门禁进入真实实施。

### Acceptance Criteria

1. 首轮集成回归结论可追踪。
2. 并行开发准入条件明确。
3. 合并顺序、最小测试集和 gate 口径统一。
4. 不在本 Story 中承接新的结构性迁移工作。
