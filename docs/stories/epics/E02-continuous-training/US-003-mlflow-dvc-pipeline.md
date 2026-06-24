# US-003 MLflow + DVC continuous training pipeline

## Status

in_progress

## Lane

normal

## Product Contract

Deliver a continuous training path:

- MLflow tracking server (Compose) with S3 artifact backend
- DVC pipeline with S3 remote template
- CLI: `./llm-local train pipeline {run|repro|schedule}`
- `register` stage creates draft release linked to MLflow run

## Relevant Product Docs

- `docs/product/continuous-training.md`
- `docs/product/data-versioning.md`
- `docs/product/experiment-tracking.md`
- `docs/decisions/002-mlflow-dvc-s3-continuous-training.md`

## Acceptance Criteria

- `training/mlflow/docker-compose.yml` starts MLflow with S3 env configuration
- `training/pipeline/dvc.yaml` defines 4 stages
- `./llm-local train pipeline repro --dry-run` completes without GPU
- Product docs and ADR published
- TEST_MATRIX row added

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | pytest for pipeline scripts (dry-run) |
| Integration | dvc.yaml + compose config valid; dry-run repro |
| Platform | full repro on GPU VM with S3 + MLflow (manual) |
| Release | N/A |

## Evidence

<!-- evidence-metadata
validated_at: 2026-06-24
host_type: local
gpu: none
commands:
- .venv/bin/python -m pytest tests/test_training_pipeline.py -q
- .venv/bin/python -m llm_local.validation integration
stale_when:
- dvc.yaml changes
- pipeline scripts change
-->

Local proof: pytest 3/3 passed; dry-run pipeline creates draft release in registry.
S3 + MLflow server + GPU full repro pending on prepared VM.
