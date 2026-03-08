# Story EPIC4-S5：旧测试口径清理与 baseline 建立

状态：ready-for-dev

## 用户故事

作为 `lane-06` owner，
我希望清理仍绑定旧链路的测试口径并建立 EPIC4 baseline，
以便后续结构拆分时能够区分“旧 seam 问题”和“现行主链问题”。

## owned surface

1. `tests/`
2. `services/*/tests/`
3. `docs/09_测试与验收/`
4. `docs/99_研发过程管理/14_EPIC-重构实施基线落位/测试/`

## 依赖

1. 与 `EPIC4-S3`
2. 与 `EPIC4-S4`

## 验收标准

1. 形成 smoke baseline。
2. 形成 known-fail 清单。
3. 建立统一验证入口。
4. 明确哪些失败属于旧 seam，哪些属于主链真实回归。

## 最小测试 / 验收

1. 仓库卫生检查
2. baseline 入口命令核对
3. known-fail 清单人工验收

## Ring1 影响判断

1. 可能影响正式测试方法文档，实施时需回填 `docs/09_测试与验收/`。
