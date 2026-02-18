# 工厂系统工艺Agent最短路径调试（2026-02-14）

## 调试范围（本阶段）
- 仅调试工厂系统内部工艺Agent能力。
- 不做产线到工厂的端到端联调。
- 验证目标：
  1) LLM参与的工艺设计（design_process）
  2) 自迭代修改（modify_process）
  3) 工具包构建脚本生成与LLM归并

## 测试入口
- 测试文件：`tests/test_factory_process_expert_short_path.py`
- 一键脚本：`scripts/run_factory_process_expert_short_path.sh`

## 执行命令
```bash
cd /Users/huda/Code/worktrees/factory-address-verify
export MAP_TOOLPACK_API_URL="<your_map_toolpack_api_url>"
export MAP_TOOLPACK_API_KEY="<your_map_toolpack_api_key>"   # 可选
export MAP_TOOLPACK_SEED_ADDRESS="上海市黄浦区中山东一路1号"     # 可选

./scripts/run_factory_process_expert_short_path.sh
```

说明：默认就是**真实模式**（真实 LLM + 真实地图 API）。

## 真实配置模式（可选）
```bash
cd /Users/huda/Code/worktrees/factory-address-verify
./scripts/run_factory_process_expert_short_path.sh
```

说明：
- 默认启用真实 LLM + 真实地图 API 的短路径测试。
- 仍不触发产线端到端链路，仅在工厂系统内部验证工艺Agent迭代与工具包生成。

## 本地快测模式（显式指定）
```bash
cd /Users/huda/Code/worktrees/factory-address-verify
./scripts/run_factory_process_expert_short_path.sh --mock
```

## 覆盖点
1. design_process + ProcessCompiler：验证 `tool_scripts` 生成（含 data_generator 脚本）。
2. modify_process：验证同一工艺编码的迭代草案生成与阈值提升。
3. AddressToolpackBuilder：验证地图API观测 + LLM归并输出 toolpack 结构。

## 说明
- 该测试使用 mock/stub 驱动工厂侧依赖，确保最短调试反馈回路。
- 若要切换为真实地图API与真实LLM，仅需替换 builder 入参与 config。
