# Spatial-Intelligence Data Factory PM Repo

This repository stores project management requirements and execution logs for a multi-person, multi-AI, multi-tool workflow.

## Scope

- Daily key deliverables tracking
- Per-member work logs
- Team-level daily/weekly summary
- Cross-tool machine-readable format (Markdown + YAML front matter + JSON Schema)

## Directory Layout

- `PROJECT_MANAGEMENT_REQUIREMENTS.md`: Project management policy and mandatory logging rules.
- `logs/daily/`: Daily project-level entries (`YYYY-MM-DD.md`).
- `logs/members/`: Per-member logs (`<member-id>/YYYY-MM-DD.md`).
- `logs/summary/`: Team summaries (`weekly-YYYY-Www.md`, `monthly-YYYY-MM.md`).
- `templates/`: Reusable Markdown templates.
- `schemas/`: JSON schemas for validation.

## Naming Convention

- Date format: `YYYY-MM-DD` (ISO-8601)
- Week format: `YYYY-Www` (ISO week)
- Member ID: lowercase kebab-case (example: `li-ming`, `agent-codex`)

## Interoperability Contract

- Human-readable: Markdown
- AI/tool-readable: YAML front matter + JSON Schema
- Timezone field required in all logs (`Asia/Shanghai`, `UTC`, etc.)
- Every entry must include traceable evidence links (PR, issue, commit, doc path)
