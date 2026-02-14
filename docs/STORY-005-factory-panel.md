# STORY-005（工厂侧）：双产线执行结果回拉与面板展示

## 目标
在工厂项目中展示两个产线（公安地址治理、城市治理）的执行结果。
后台服务负责定时从两个产线仓库 `output/*.json` 拉取并聚合。

## 启动方式
```bash
cd /Users/huda/Code/spatial-intelligence-data-factory
python3 scripts/factory_story5_panel_server.py
```

打开：`http://127.0.0.1:8866`

## API
- `/api/summary`
- `/api/line/public_security_address/latest`
- `/api/line/public_security_address/history`
- `/api/line/urban_governance/latest`
- `/api/line/urban_governance/history`
