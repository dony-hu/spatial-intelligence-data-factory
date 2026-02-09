# Project Management Requirements

## 1. Objective

Create a durable process record that can be understood by different contributors, AI coding environments, and toolchains.

## 2. Mandatory Logging Objects

1. Project daily key output log
2. Individual member daily log
3. Team summary log (weekly/monthly)

## 3. Required Fields (All Logs)

- `date`
- `timezone`
- `author`
- `role`
- `work_items`
- `deliverables`
- `risks`
- `next_actions`
- `evidence_links`
- `updated_at`

## 4. Governance Rules

1. Every contributor must submit a daily log before end-of-day.
2. Every deliverable entry must map to at least one evidence link.
3. Weekly summary must aggregate:
- completed outputs
- blocked items
- risk trend
- next-week priorities
4. Any scope or architecture decision change must be recorded in logs on the same day.
5. Logs are append-only for history. If corrections are required, add a correction entry with timestamp.

## 5. Definition of Done (Log Compliance)

A day is compliant only if:
1. Project daily log exists.
2. Each active contributor has an individual log.
3. Evidence links are valid and reachable in repository/tooling context.
4. Next actions are explicit and executable.

## 6. Cross-Environment Compatibility Standard

1. Markdown files must use UTF-8 and Unix line endings.
2. Front matter must be valid YAML.
3. Fields must conform to `schemas/worklog.schema.json`.
4. Prefer stable IDs over free text when possible (`task_id`, `epic_id`, `story_id`).

## 7. Recommended Automation

1. CI validation for front matter + JSON Schema compliance.
2. Daily check for missing member logs.
3. Weekly auto-generation of summary draft from individual logs.
