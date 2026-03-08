# Story EPIC15-S5：新编排内核合同回归测试与替换验收

状态：ready-for-dev

## 用户故事

作为 `lane-06` owner，
我希望为 Agent 框架替换试点建立新编排内核的合同回归测试与替换验收口径，
以便团队能明确判断新骨架是否真的承接了现行正式行为，而不是只完成了技术接线。

## owned surface

1. `tests/`
2. `services/*/tests/`
3. `docs/09_测试与验收/`
4. `docs/99_研发过程管理/15_EPIC-Agent框架替换试点/`

## 依赖

1. `EPIC15-S3`
2. `EPIC15-S4`

## 验收标准

1. 新编排内核合同回归测试入口已建立。
2. 合同回归测试至少覆盖：
   - requirement query
   - blueprint generation
   - dryrun / publish 触发
   - human gate / blocked / recover
3. façade 对外合同未破坏。
4. 试点验收结论明确区分：
   - 可放行行为
   - 已知差异
   - 暂不放行行为
5. 输出不提前承诺 Runtime 控制层替换结论。

## 最小测试 / 验收

1. 合同回归测试
2. smoke baseline
3. known-diff / known-fail 清单

## Ring1 影响判断

1. 一般不直接改变 Ring1 正式设计。
2. 若合同回归测试暴露正式边界差异，需反馈到相关 Ring1 正式文档。
