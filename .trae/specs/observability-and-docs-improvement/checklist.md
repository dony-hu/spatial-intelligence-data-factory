# Checklist

## P0 - 立即行动（高优先级）
- [x] `.gitignore` 已添加 `.venv/` 忽略规则
- [x] `.venv/` 未被 Git 跟踪（从历史中移除）
- [x] E2E 测试通过后自动调用 `collect_governance_metrics.py`
- [x] 看板自动化集成已验证（运行一次 E2E 测试，确认看板更新）

## P1 - 短期（中优先级）
- [x] 文档硬编码路径扫描已完成（识别 30+ 处）
- [x] 文档路径批量替换已执行（绝对路径 → 相对路径）
- [x] 关键文档路径验证通过（README、quickstart 等）

## P2 - 中期（可选）
- [ ] （可选）pydantic-settings 已引入
- [ ] （可选）配置加载逻辑已重构
