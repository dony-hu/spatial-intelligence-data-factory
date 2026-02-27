# bmad-story-deliver 标准输入

## 必需文件

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/<story-key>.md`（`story-key` 格式：`X-Y-story-name`）

## 必需约束

- `sprint-status.yaml` 的 `stories` 仅允许：`backlog | ready-for-dev | in-progress | done`
- 每个 `stories` 条目必须有同名 story 文档
- 每个 story 文档必须包含：
  - `Status: <status>` 行，且与 `sprint-status.yaml` 保持一致
  - `## Tasks` 或 `## 任务清单` 段落
  - 至少一条任务勾选项（`- [ ]` 或 `- [x]`）

## 一键校验

```bash
python3 scripts/validate_bmad_story_deliver_inputs.py --base-dir .
```

当前校验输出应包含：

```text
PASS: bmad-story-deliver 标准输入校验通过
NEXT_BACKLOG_STORY=1.6
```
