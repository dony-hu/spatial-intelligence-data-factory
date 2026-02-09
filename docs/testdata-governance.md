# Test Data Governance

## Scope

This document defines how test datasets are created, stored, versioned, and consumed in this repository.

## Dataset Policy

1. Allowed data classes: `synthetic`, `masked`.
2. Forbidden in Git: raw production exports, unmasked PII, large snapshots.
3. Every dataset must be registered in `testdata/catalog/catalog.yaml`.

## Naming

- Dataset ID: `<domain>_<scenario>_<level>` (example: `geo_poi_smoke_p0`).
- Version: `vYYYY.MM.DD.N`.
- File name: `<dataset_id>__<version>__<format>.<ext>`.

## Metadata Requirements

Each catalog entry must include:

- `id`, `version`, `level`, `purpose`, `owner`, `source`
- `pii` (`none|masked|synthetic`)
- `retention_days`
- `storage` (`type`, `uri`)
- `checksum` (`algo`, `value`)

## Lifecycle

1. Register request in `catalog.yaml`.
2. Generate or mask dataset.
3. Compute checksum.
4. Commit fixture (small only) or upload large data to object storage.
5. Use `scripts/testdata/pull.sh` and `scripts/testdata/verify.sh` in CI.
6. Remove expired datasets based on `retention_days`.

## Access Control

- Object storage access must use least privilege and short-lived credentials.
- Environment isolation required (`dev`, `test`, `stage`).
- Direct access to raw source data is restricted to approved operators.
