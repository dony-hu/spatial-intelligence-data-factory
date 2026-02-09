# TOOLING ADAPTERS

## Objective

Map previous Codex-specific operating rules into project-level requirements that can be enforced in any AI coding IDE/toolchain.

## Mapping Principles

1. Keep project requirement semantics unchanged across tools.
2. Treat tool-specific syntax as implementation detail.
3. Keep policy in repository, not in chat memory.

## Codex-to-Project Mapping

### A. Communication and Output

- Codex behavior: concise, structured, actionable responses.
- Project requirement: all implementation reports MUST include scope, changes, validation, and next actions.
- Cross-tool implementation: PR template and change summary checklist.

### B. Work Execution

- Codex behavior: inspect before edit, verify after edit, avoid destructive commands.
- Project requirement: changes MUST include pre-change context capture and post-change verification evidence.
- Cross-tool implementation: commit checklist + CI logs + rollback note.

### C. Engineering Quality

- Codex behavior: lint/test/build before completion when applicable.
- Project requirement: pre-merge quality gates are mandatory.
- Cross-tool implementation: CI pipeline with blocking checks.

### D. Collaboration and Handoff

- Codex behavior: frequent progress updates and explicit assumptions.
- Project requirement: each meaningful milestone MUST be logged with owner, timestamp, impact, and evidence links.
- Cross-tool implementation: daily logs + weekly summary.

### E. Safety and Security

- Codex behavior: do not leak secrets, cautious escalation.
- Project requirement: no plaintext secrets in repo; least privilege; audit trail required.
- Cross-tool implementation: secret scanning + access review.

### F. Tool Operations

- Codex behavior: skills, sandbox, escalation prefixes.
- Project requirement: tool operational rules MAY vary, but MUST preserve governance, security, and traceability outcomes.
- Cross-tool implementation: maintain per-tool runbook without changing project policy.

## Per-Tool Adapter Template

Use this section for each tool (Codex/Cursor/Claude Code/etc.):

- Tool name:
- Environment constraints:
- Command execution model:
- Approval/escalation flow:
- Required checks before merge:
- Logging path and format:
- Known limitations:

## Current Status

- Project-level policies are stored in `PROJECT_REQUIREMENTS.md`.
- Logging standards are stored in `PROJECT_MANAGEMENT_REQUIREMENTS.md` and `schemas/worklog.schema.json`.
- Tool-specific behavior should be added only as adapters in this file.
