# Overview — US-011 DVC subproject + S3 remote hardening

## Status

planned

## Lane

high-risk

## Current Behavior

- `training/pipeline/dvc.yaml` defines four stages; `dvc.lock` may exist locally.
- `llm_local/pipeline/runner.py` falls back to sequential stage execution when DVC
  is missing or `.dvc/` is uninitialized.
- US-003 platform proof ran `dvc repro` manually; CI uses pytest stage modules and
  dry-run paths without remote I/O.
- Brooks-Lint noted empty `.dvc/` on another host; this workspace has config/cache
  but lacks automated remote proof.

## Target Behavior

- DVC subproject is the canonical repro path; fallback is emergency-only and logged.
- Operators configure S3 remote via `config.local` + env vars per
  `docs/product/data-versioning.md`.
- Integration tests exercise `dvc repro` and document push/pull/status commands.
- **Dev proof first**: MinIO via `config/env/mlflow.env` (`s3://mlops-platform/dvc-storage`).
- **Production**: documented operator path for AWS S3 bucket (same prefix, IAM, no endpoint).
- No DVC stage performs git commit, tag, or push.

## Affected Users

- ML engineer running `./llm-local train pipeline repro`
- Platform operator provisioning S3/MinIO

## Affected Product Docs

- `docs/product/data-versioning.md`
- `docs/product/continuous-training.md`
- `docs/decisions/002-mlflow-dvc-s3-continuous-training.md`

## Non-Goals

- Replacing MLflow with DVC for model artifacts
- Adding W&B
- Migrating pipeline root away from `training/pipeline/`

## Intake reference

- `docs/intake/2026-07-02-brooks-lint-dvc-ct-audit.md`
