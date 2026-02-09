# PROJECT REQUIREMENTS

## 1. Purpose

Define tool-agnostic project requirements that work across teams and AI coding environments.

## 2. Scope

Applies to requirement management, delivery process, quality gates, worklogs, and security controls.

## 3. Requirement Levels

- MUST: mandatory, non-compliance blocks delivery.
- SHOULD: recommended default.
- MAY: optional enhancement.

## 4. Governance

### 4.1 Ownership

- MUST assign `Project Owner`, `Tech Lead`, and `Release Owner`.
- MUST assign one clear owner to each work item.
- SHOULD assign backup owner for critical streams.

### 4.2 Decision Traceability

- MUST record major decisions in ADR-like form.
- MUST include context, options, decision, impact, and rollback condition.
- SHOULD review unresolved risks weekly.

## 5. Delivery Process

### 5.1 Requirement to Delivery

- MUST define acceptance criteria before implementation.
- MUST keep tasks small enough for one iteration and one validation cycle.
- SHOULD structure planning as `Epic -> Story -> Task`.

### 5.2 Branch and Commit

- MUST follow controlled branch strategy (for example `main` + feature/hotfix).
- MUST use a consistent commit format (for example Conventional Commits).
- MUST avoid direct unreviewed merge to `main`, except emergency fixes with post-review.

### 5.3 Code Review

- MUST review all code changes before merge.
- MUST check correctness, regression risk, and test coverage in review.
- SHOULD require dual review for high-risk modules.

## 6. Quality Gates

### 6.1 Pre-merge Gates

- MUST pass lint checks.
- MUST pass automated tests.
- MUST pass build validation.
- MUST include regression evidence for critical-path changes.

### 6.2 Release Gates

- MUST provide release change list and rollback plan.
- MUST ensure observability for key signals (error rate, latency, availability).
- SHOULD run a short post-release stabilization check.

## 7. Worklog Standard

### 7.1 Daily Project Log

- MUST record daily key outputs, risks, and next actions.
- MUST attach at least one evidence link for each key output.

### 7.2 Member Daily Log

- MUST require each active contributor to submit one daily log.
- MUST include work items, outputs, blockers, and next steps.

### 7.3 Team Summary

- MUST publish weekly summary: completed items, blockers, risk trend, next-week priorities.
- SHOULD publish monthly summary with KPI comparison.

## 8. Security and Compliance

- MUST NOT store plaintext secrets/tokens in repository or logs.
- MUST apply least privilege for data, systems, and APIs.
- MUST keep auditable trace of changes.
- SHOULD run security review for high-risk changes.

## 9. Tool-Agnostic Policy

- MUST keep requirements independent from any single AI tool.
- MUST make key processes readable, executable, and auditable in repository docs.
- SHOULD maintain per-tool adapters without changing project requirement semantics.

## 10. Definition of Done

A work item is done only when all are true:

- MUST pass functional acceptance.
- MUST pass quality gates.
- MUST update required docs and logs.
- MUST record residual risks and next actions.
