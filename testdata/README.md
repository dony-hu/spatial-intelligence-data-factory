# Test Data Workspace

This directory stores test data assets and metadata for repeatable testing.

## Structure

- `fixtures/`: small, Git-tracked datasets for unit/integration smoke tests.
- `seeds/`: generated local seed datasets (keep files small).
- `contracts/`: schema and field-level constraints for validation.
- `catalog/`: dataset registry (`catalog.yaml`) and checksums.
- `downloads/`: pulled large datasets from object storage (ignored by Git).
- `cache/`: transient cache for scripts (ignored by Git).
- `tmp/`: temporary files (ignored by Git).

## Rules

1. Only `synthetic` or `masked` datasets can be committed.
2. Do not commit large binary/raw snapshots; store them in object storage.
3. Every dataset must have metadata in `catalog/catalog.yaml`.
4. Always verify checksum before running tests in CI.
