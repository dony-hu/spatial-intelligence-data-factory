# Story: RE5-S2 quick_test 集成验收

## 目标

将 `quick_test` 作为 P0 回归基线。

## 验收标准

1. 每条 case 清洗成功。
2. 每条 case 图谱 `nodes>0 && relationships>0`。
3. 不允许 `completed` 且图谱空产物。
4. 集成测试在 CI 可自动执行。

## 开发任务

1. 新增集成测试脚本，运行 `quick_test` 并断言。
2. CI workflow 加入该脚本。
3. 失败时输出可定位日志。
