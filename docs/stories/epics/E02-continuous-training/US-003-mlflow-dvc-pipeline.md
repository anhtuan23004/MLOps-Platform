# US-003 MLflow + DVC continuous training pipeline

## Status

implemented

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
- Pipeline stage execution does not require a hard-coded repo-local Python path
- Fresh env bootstrap initializes `training/pipeline/.dvc/config` from template when absent
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
validated_at: 2026-06-29
host_type: local GPU host
gpu: NVIDIA GeForce RTX 3060
commands:
- .venv/bin/python -m pytest tests/test_training_pipeline.py -q
- make test-integration
- RELEASE_REGISTRY_ROOT=/tmp/mlops-portable-registry ./llm-local train pipeline run --dry-run
- ./llm-local train mlflow up
- cd training/pipeline && MLFLOW_TRACKING_URI=http://localhost:15000 AWS_ACCESS_KEY_ID=mlops AWS_SECRET_ACCESS_KEY=mlops-secret AWS_DEFAULT_REGION=us-east-1 AWS_ENDPOINT_URL=http://localhost:19000 CT_DRY_RUN=false UNSLOTH_TRAIN_SIMULATE=1 RELEASE_REGISTRY_ROOT=/home/dev/MLOps-Platform/training/pipeline/.state/release-registry ../../.venv/bin/dvc repro -f
stale_when:
- dvc.yaml changes
- run_stage.sh changes
- pipeline scripts change
- mlflow_registry.py changes
- register.py changes
-->

Local proof (2026-06-29): pytest 4/4 passed; `make test-integration` passed and
covered training pipeline unit/integration checks with dry-run-compatible
artifacts.

Portability proof (2026-06-29): `./llm-local train pipeline run --dry-run`
completed through the standard CLI with `RELEASE_REGISTRY_ROOT=/tmp/mlops-portable-registry`.
The pipeline now uses `training/pipeline/run_stage.sh` instead of a hard-coded
`.venv/bin/python` path inside `dvc.yaml`, and the runner bootstraps
`training/pipeline/.dvc/config` from `config/dvc/config.example` when the DVC
config file is absent in a fresh environment.

Platform proof (2026-06-29): `./llm-local train mlflow up` exposed a healthy
local MLflow + MinIO stack on the workspace host, then `dvc repro -f` completed
end-to-end with `CT_DRY_RUN=false` and `UNSLOTH_TRAIN_SIMULATE=1`. The resulting
`training/pipeline/models/artifacts/run_manifest.json` recorded
`run_id=a10b69e65f3f4605aee84417a2c64c66`,
`model_uri=models:/mlops-ct-model/4`, and `dry_run=false`. The register stage
created draft release `rel-ct-9b455045`, recorded in
`training/pipeline/data/pipeline/release_pointer.json`.

Workspace note: the default registry root under `data/release-registry/` is not
writable in this environment, so platform proof used
`RELEASE_REGISTRY_ROOT=training/pipeline/.state/release-registry` as the writable
fallback registry path.
