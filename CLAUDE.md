# Claude Code 项目入口说明（BMAD）

## 读取顺序
1. `AGENTS.md`
2. `bmad/config.yaml`
3. `docs/bmm-workflow-status.yaml`

## 方法仓定位
- 默认：`/Users/01411043/code/BMAD-METHOD`
- 回退：`${BMAD_METHOD_REPO}`

## 执行前检查
在执行 BMAD 命令前，确认方法仓资产存在：
- `${BMAD_METHOD_REPO:-/Users/01411043/code/BMAD-METHOD}/_bmad`
- `${BMAD_METHOD_REPO:-/Users/01411043/code/BMAD-METHOD}/docs`

## 约束
1. 不得臆造 BMAD 角色、命令或模板结构。
2. 若方法仓不可达，需显式告知并使用项目内回退配置。
3. 文档默认中文，代码改动遵循测试优先。
