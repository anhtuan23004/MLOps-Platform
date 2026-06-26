# Continuous Training on GPU VM — MLOps-Platform

Runbook for **US-004**: real Unsloth fine-tune with MLflow Model Registry.

## Prerequisites

- GPU VM with NVIDIA drivers + Docker
- `llm-net` network: `make network`
- **Local dev**: `./llm-local train mlflow up` brings up Postgres + MinIO + MLflow
  (see `config/env/mlflow.env.example`). Set DVC remote to the same bucket:
  `s3://mlops-platform/dvc-storage` with `AWS_ENDPOINT_URL=http://localhost:19000`.
- **Production**: S3 + external Postgres via release/CI-CD (`AWS_*`, no MinIO endpoint).
- DVC remote: `cp config/dvc/config.example training/pipeline/.dvc/config` (edit bucket)
- Base model present under `models/<id>/` (e.g. `./llm-local model download ...`)

## Steps

```bash
# 1. Config
./llm-local config init
./llm-local config init
vim config/env/mlflow.env      # defaults: local MinIO + Postgres; prod: external S3
vim config/pipeline/params.yaml  # set train.dry_run: false

# 2. Start services
./llm-local train mlflow up
./llm-local train up           # Unsloth GPU container

# 3. Run pipeline (no dry-run)
export MLFLOW_TRACKING_URI=http://localhost:15000
export CT_DRY_RUN=false
./llm-local train pipeline run
# or: cd training/pipeline && dvc repro

# 4. Verify
# - MLflow UI: experiment run + registered model mlops-ct-model
# - training/pipeline/models/artifacts/staging/ adapter files
# - training/pipeline/models/artifacts/run_manifest.json → mlflow.model_uri
# - Draft release in data/release-registry/
```

## Simulate without GPU (dev only)

```bash
export UNSLOTH_TRAIN_SIMULATE=1
export CT_DRY_RUN=false
# Requires MLflow server up for register_model
./llm-local train pipeline run
```

## Troubleshooting

| Issue | Action |
| --- | --- |
| `Unsloth container not running` | `./llm-local train up` |
| MLflow register fails | Check `MLFLOW_TRACKING_URI` and S3 credentials |
| Base model not found in container | Verify `models/` mount and `model.base_model` in params |

## Promotion

Pipeline `register` creates a **draft** release only. Promote manually:

```bash
./llm-local release promote <ID> --to dev --apply-serving
```

See [`release-promotion-vm.md`](release-promotion-vm.md).
