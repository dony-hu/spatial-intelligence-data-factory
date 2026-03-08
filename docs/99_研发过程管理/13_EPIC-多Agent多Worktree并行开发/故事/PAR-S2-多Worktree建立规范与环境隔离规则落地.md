# PAR-S2 多Worktree建立规范与环境隔离规则落地

## 1. 目标

建立多 Worktree 的目录、命名、创建和回收规则，并明确本地环境隔离方式。

## 2. 交付物

1. Worktree 目录规范
2. branch 命名规范
3. 本地 `.venv / .env / output / DB` 隔离约定

## 3. 验收标准

1. Worktree 不嵌套在主仓内部。
2. 每条 Lane 都能用统一命名方式创建 Worktree。
3. 不同 Worktree 的本地依赖和运行产物不会互相污染。
