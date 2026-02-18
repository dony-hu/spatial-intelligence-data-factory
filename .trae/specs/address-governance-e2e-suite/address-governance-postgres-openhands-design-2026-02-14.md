# [已废弃] 地址治理目标态架构设计（Postgres + FastAPI/Pydantic + OpenHands）

> **⚠️ 重要说明（2026-02-19）**
> 本文档已废弃，仅作为技术设计参考。
> 最新设计请参考：[spec.md](spec.md)
> 
> **主要差异：**
> 1. **执行层**：OpenHands 集成方式已变更为 Factory Agent + Workpackage 模式。
> 2. **API 层**：工厂 CLI 统一使用 `converse()` 接口，不再直接暴露 FastAPI 端点。
> 3. **数据模型**：以 `spec.md` 中定义的 schema 为准。

---

## 历史内容（仅供参考）

### 1. 目标与边界
...（后续内容保持不变）
