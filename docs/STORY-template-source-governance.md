# Story: 产线面板模板来源治理（第一步）

## 目标
将产线监控/测试调试面板模板统一收敛到工厂项目输出，产线只做模板消费与最小参数注入。

## 第一阶段交付
- 工厂模板：`templates/line_debug_panel.template.html`
- 工厂发布脚本：`scripts/publish_line_panel_templates.py`
- 发布目录：`output/factory_templates/`

## 规则
- 产线仓库不得维护独立定制 HTML 模板。
- 产线面板服务只读取工厂模板，并注入输入字段、标题、默认样例。
