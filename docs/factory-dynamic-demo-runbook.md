# 工厂动态演示运行手册

## 1. 目标

通过后台任务持续执行用例，并自动清理演示环境数据，保证看板持续有动态变化且不会长期累积脏数据。

## 2. 一键后台运行

启动：

```bash
/Users/01411043/code/spatial-intelligence-data-factory/scripts/factory_demo_daemon.sh start
```

如端口 `5000` 被占用：

```bash
DEMO_PORT=5052 /Users/01411043/code/spatial-intelligence-data-factory/scripts/factory_demo_daemon.sh start
```

停止：

```bash
/Users/01411043/code/spatial-intelligence-data-factory/scripts/factory_demo_daemon.sh stop
```

状态：

```bash
/Users/01411043/code/spatial-intelligence-data-factory/scripts/factory_demo_daemon.sh status
```

日志：

```bash
/Users/01411043/code/spatial-intelligence-data-factory/scripts/factory_demo_daemon.sh logs
```

## 3. 看板地址

- 实时看板：<http://127.0.0.1:5000>

## 4. 默认运行策略

- 用例来源：`scenario`（按 `quick_test/address_cleaning/entity_fusion/relationship_extraction` 轮询）
- 每轮用例数：`30`
- 每条间隔：`1s`
- 每轮结束等待：`3s`
- 自动清理：开启（每轮重置 `database/factory_demo_runtime.db`）

## 5. 自定义运行参数

直接运行 Python 脚本：

```bash
python3 /Users/01411043/code/spatial-intelligence-data-factory/scripts/factory_continuous_demo_web.py \
  --host 127.0.0.1 \
  --port 5000 \
  --case-mode scenario \
  --cases-per-cycle 50 \
  --max-cycles 0 \
  --case-interval 0.8 \
  --reset-interval 2 \
  --cleanup-each-cycle
```

说明：`--max-cycles 0` 表示无限循环。
