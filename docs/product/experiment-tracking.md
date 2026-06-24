# Experiment Tracking (MLflow) — MLOps-Platform

## Role

MLflow tracks **training runs**, **parameters**, **metrics**, and **model artifacts**
for continuous training and promotion decisions.

## Tracking server

Docker Compose: `training/mlflow/docker-compose.yml`

Default tracking URI: `http://localhost:15000` (override with `MLFLOW_TRACKING_URI`).

## Artifact storage

Artifacts stored in **S3** (`MLFLOW_S3_BUCKET`). Metadata backend uses a local
SQLite/file store in the MLflow container volume (sufficient for single-VM setups).

Environment:

| Variable | Purpose |
| --- | --- |
| `MLFLOW_TRACKING_URI` | Client + pipeline target |
| `MLFLOW_S3_BUCKET` | S3 bucket for artifacts |
| `AWS_*` | Same credentials as DVC remote |

## Model registry

Training pipeline logs a run and registers a model version:

- **Experiment**: `mlops-platform-continuous-training`
- **Registered model name**: from `config/pipeline/params.yaml` → `model.name`

Release registry (`data/release-registry/`) references MLflow run ID and model URI
in the `register` pipeline stage.

## UI

After `./llm-local train mlflow up`, open `http://localhost:15000`.
