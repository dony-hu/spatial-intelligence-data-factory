# Router/Gate 阈值配置说明

日期：2026-02-14

## 1. 配置来源优先级

1. 环境变量（最高优先级）
2. 文件配置：`settings/router_gates.json`
3. 内置默认值（兜底）

## 2. 配置项

- `max_steps`：最大轮次数门禁
- `max_cost_usd`：总成本门禁
- `max_duration_sec`：总时长门禁（秒）
- `cost_per_1k_tokens_usd`：每 1k token 成本估算单价

## 3. 环境变量映射

- `FACTORY_ROUTER_GATES_PATH`
- `FACTORY_GATE_MAX_STEPS`
- `FACTORY_GATE_MAX_COST_USD`
- `FACTORY_GATE_MAX_DURATION_SEC`
- `FACTORY_GATE_COST_PER_1K_TOKENS_USD`

## 4. 变更与回滚建议

1. 先在灰度环境调整单项阈值并观察 `budget_gate` 输出。
2. 生产变更建议单次只改一个阈值，便于归因。
3. 若出现误拦截，优先回滚环境变量；未设置环境变量时回滚 `settings/router_gates.json` 并重启服务。

