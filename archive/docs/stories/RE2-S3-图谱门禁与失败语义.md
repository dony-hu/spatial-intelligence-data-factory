# Story: RE2-S3 图谱门禁与失败语义

## 目标

确保图谱空产物不再被标记为成功。

## 验收标准

1. `nodes==0` 或 `relationships==0` 时状态为 `FAILED`。
2. 错误码为 `GRAPH_EMPTY_OUTPUT`。
3. 失败不重试。

## 开发任务

1. 在 `tools/factory_workflow.py` 增加 `GraphGate`。
2. Gate 失败时落库失败状态与原因。
3. 调整 summary 与看板状态映射。
