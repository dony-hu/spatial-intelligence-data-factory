# Trae 项目说明（BMAD）

## 单一事实源
- `AGENTS.md`
- `bmad/config.yaml`
- `docs/bmm-workflow-status.yaml`

## 方法仓引用
1. 默认路径：`/Users/01411043/code/BMAD-METHOD`
2. 环境变量回退：`BMAD_METHOD_REPO`
3. 资产要求：`_bmad/`、`docs/`

## 工作流执行要求
1. 执行 `/workflow-status`、`/prd`、`/architecture`、`/create-story`、`/dev-story` 前，先校验方法仓可达。
2. 项目规则优先级：`AGENTS.md` > `bmad/config.yaml` > 方法仓模板。
3. 若方法仓不可用，需显式说明并采用项目内回退配置。
