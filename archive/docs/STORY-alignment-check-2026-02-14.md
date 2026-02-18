# Story 对齐检查报告（2026-02-14）

## 范围
- 工厂项目：`/Users/huda/Code/worktrees/integration`
- 产线项目 A：`/Users/huda/Code/si-factory-public-security-address`
- 产线项目 B：`/Users/huda/Code/si-factory-urban-governance`

## 检查维度
1. Story 是否有对应实现脚本
2. Story 是否有对应输入/输出契约或样例
3. 面板模板是否由工厂项目统一产出
4. 是否具备 run/clean/panel_up 三类运维脚本
5. 是否具备“一键拉起三面板”总控入口

## 对齐结果（按 Story）

### STORY-001（公安地址治理产线）
- 状态：已落地（MVP）
- 证据：
  - `si-factory-public-security-address/src/address_line.py`
  - `si-factory-public-security-address/scripts/run_address_line.py`
  - `si-factory-public-security-address/contracts/address_line_*.schema.json`

### STORY-002（景情关系图谱产线）
- 状态：已落地（MVP）
- 证据：
  - `si-factory-urban-governance/src/scene_line.py`
  - `si-factory-urban-governance/scripts/run_scene_line.py`
  - `si-factory-urban-governance/contracts/scene_graph_*.schema.json`

### STORY-003（工作包自展开执行）
- 状态：已落地
- 证据：
  - `*/scripts/self_expand_runner.py`
  - `*/workpackages/wp-*.json`

### STORY-004（地址治理自动化执行+图谱）
- 状态：已落地
- 证据：
  - `si-factory-public-security-address/scripts/run_story.sh`

### STORY-005（面板与回拉展示）
- 状态：已落地（分层）
- 工厂侧：
  - 结果回拉面板：`scripts/factory_story5_panel_server.py`
  - 工艺专家对话室：`scripts/factory_process_dialog_room.py`
- 产线侧：
  - `*/scripts/panel_server.py`

### STORY-006（警情数据接入并部署到城市治理产线）
- 状态：已落地
- 证据：
  - `si-factory-urban-governance/testdata/police_incidents.sample.json`
  - `si-factory-urban-governance/scripts/deploy_story6_to_line2.py`

## 模板来源治理检查
- 结果：通过
- 说明：
  - 工厂模板：`templates/line_debug_panel.template.html`
  - 发布脚本：`scripts/publish_line_panel_templates.py`
  - 产线面板仅消费工厂发布模板并做参数注入。

## 需补充项（本轮）
1. README 级入口缺失：需明确 run/clean/panel_up 命令。
2. 工厂总控入口说明需写入主 README。

## 落地启动口令（当前推荐）
```bash
/Users/huda/Code/worktrees/integration/scripts/panel_up_all.sh
```
