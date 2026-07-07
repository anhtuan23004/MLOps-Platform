# Decisions

Architecture and product decisions for MLOps-Platform live here.

Use `docs/templates/decision.md` for new records. Historical source-project decisions
were intentionally not copied into this blank harness.

## Records

| Decision | Status | Summary |
| --- | --- | --- |
| [ADR-002: MLflow + DVC on S3 for Continuous Training](002-mlflow-dvc-s3-continuous-training.md) | Accepted | Use DVC for dataset/pipeline lineage and MLflow with S3-compatible artifacts for continuous training. |
| [ADR-003: Modular Monorepo Before Repository Split](003-modular-monorepo-before-repo-split.md) | Accepted | Keep one repo, enforce folder ownership seams, and split only when ownership or release cadence requires it. |
