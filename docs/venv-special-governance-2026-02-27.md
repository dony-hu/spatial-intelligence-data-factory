# `.venv` 专项治理记录（2026-02-27）

## 1. 背景

工作区历史上将 `.venv` 纳入了 Git 跟踪，导致本地 Python 解释器重建时产生大规模噪音变更，影响代码评审与提交质量。

## 2. 治理目标

1. `.venv` 与 `.venv.broken*` 不再被 Git 跟踪。
2. 仓库具备自动化检查，防止虚拟环境文件再次入库。
3. 与 PRD 工程治理目标（可移植性、仓库整洁度）对齐。

## 3. 本次落地动作

1. 索引治理：
- 执行 `git rm -r --cached .venv`，取消 `.venv` 跟踪（保留本地文件）。

2. 规则治理：
- `.gitignore` 已包含：
  - `.venv/`
  - `.venv.broken.*/`

3. 门禁治理：
- 新增脚本：`scripts/check_repo_hygiene.sh`
- 新增 Make 目标：`make check-repo-hygiene`

## 4. 验证结果

1. `./scripts/check_repo_hygiene.sh` 输出：
- `[ok] no tracked venv artifacts`

2. 回归测试：
- 关键主线测试与可观测性测试通过（详见 `docs/prd-progress-report-mvp-observability-2026-02-27.md`）。

## 5. 后续建议

1. 将 `make check-repo-hygiene` 纳入 CI pre-check。
2. 新成员环境初始化统一走项目脚本，避免手工迁移虚拟环境。
3. 后续若引入新本地缓存目录，按同样模式先加 ignore 再加 hygiene 检查。
