# 可信数据 HUB (Phase 1) Spec

## Why
工厂 Agent 需要访问外部可信数据源（如高德、百度、天地图）来进行 POI 验证。目前 API Key 的管理分散且不安全。需要一个集中的 `TrustHub` 模块来管理这些凭证和数据源状态。

## What Changes
- 新增 `packages/trust_hub/` 模块
- 实现 API Key 的安全存储（本地文件或环境变量）
- 提供 Python 接口供工厂 Agent 调用

## Impact
- Affected specs: `poi-shop-trust-verification`
- Affected code: `packages/factory_agent/agent.py`

## ADDED Requirements
### Requirement: API Key Management
The system SHALL provide interfaces to store and retrieve API Keys for external providers.

#### Scenario: Store API Key
- **WHEN** Factory Agent calls `store_api_key(name, key)`
- **THEN** key is saved securely

#### Scenario: List Sources
- **WHEN** Factory Agent calls `list_sources()`
- **THEN** returns list of configured providers

## MODIFIED Requirements
N/A
