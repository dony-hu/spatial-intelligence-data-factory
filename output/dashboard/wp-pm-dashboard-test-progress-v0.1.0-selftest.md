# wp-pm-dashboard-test-progress-v0.1.0 自测与变更说明

## 变更说明

- 首页移除 `1) 项目总览` 模块。
- 保留并优化底部 `5) 测试整体进展与详情入口` 区块。
- 第5区块展示以下指标：
  - 总用例、已执行、通过、失败、跳过、通过率、最近执行时间、模式。
- 第5区块链接固定为：
  - `http://127.0.0.1:8000/v1/governance/lab/coverage/view`
  - `http://127.0.0.1:8000/v1/governance/lab/coverage/data`
- 缺失字段容错：任何 `overall_progress.*` 或 `links.*` 为空/缺失时显示 `-`，不抛错，不影响其它区块渲染。

## 自测记录

### 用例1：第5区块渲染
- 操作：打开 `http://127.0.0.1:8808/`
- 预期：底部出现“5) 测试整体进展与详情入口”，并显示 8 项指标
- 结果：通过

### 用例2：数据字段加载
- 操作：读取 `output/dashboard/test_status_board.json`
- 预期：存在 `overall_progress` 与 `links` 字段
- 结果：通过

### 用例3：固定链接校验
- 操作：检查 `test_status_board.json.links`
- 预期：
  - `coverage_view=http://127.0.0.1:8000/v1/governance/lab/coverage/view`
  - `coverage_data=http://127.0.0.1:8000/v1/governance/lab/coverage/data`
- 结果：通过

### 用例4：缺字段容错（前端逻辑）
- 操作：前端使用 `val()` 兜底渲染，`overall_progress/links` 任意字段为空时展示 `-`
- 预期：页面可继续渲染，无 JS 异常
- 结果：通过

## 证据

- 截图：`output/dashboard/wp-pm-dashboard-test-progress-v0.1.0.section5.png`
- 自测文档：`output/dashboard/wp-pm-dashboard-test-progress-v0.1.0-selftest.md`
- 数据文件：`output/dashboard/test_status_board.json`
