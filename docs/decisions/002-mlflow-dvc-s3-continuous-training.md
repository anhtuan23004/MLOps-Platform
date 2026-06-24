# ADR-002: MLflow + DVC on S3 for Continuous Training

## Status

Accepted — 2026-06-24

## Context

MLOps-Platform needs reproducible data versioning, experiment tracking, and an
automated retrain path that feeds the existing release registry and promotion flow.

## Decision

1. **DVC** manages dataset snapshots and pipeline stages under `training/pipeline/`.
2. **MLflow** tracks runs and model artifacts; artifact root is **S3-compatible storage**.
3. **Triggers**: `dvc repro` on data/param changes **and** optional cron via
   `./llm-local train pipeline schedule`.
4. **Handoff**: final pipeline stage writes a draft release into the file-based
   release registry (US-002), not direct prod promotion.

## Consequences

- Operators must provision S3 bucket + IAM (or MinIO) before CT works end-to-end.
- CI uses `--dry-run` on train stage; GPU VM required for real weights.
- TensorBoard remains available but MLflow is the primary experiment UI for CT.

## Alternatives considered

- Local-only MLflow/DVC: rejected; user chose cloud S3.
- MLflow-only without DVC: rejected; data lineage needs explicit versioning.
