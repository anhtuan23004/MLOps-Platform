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

Training pipeline logs a run and registers a model version when `train.dry_run` is
false and Unsloth training succeeds:

- **Experiment**: `mlops-platform-continuous-training` (override in params)
- **Registered model name**: `config/pipeline/params.yaml` → `model.name`
- **Staging alias**: MLflow alias `staging` → latest registered version from CT

`run_manifest.json` fields used downstream:

| Field | Meaning |
| --- | --- |
| `mlflow.run_id` | Tracking run ID |
| `mlflow.model_uri` | `models:/<name>/<version>` |
| `mlflow.model_version` | Registry version integer |
| `artifact_dir` | Local adapter staging path under pipeline |

GenAI capabilities (tracing, eval, prompts): see [`mlflow-genai.md`](mlflow-genai.md)
and epic E03 stories US-005–US-007.

## UI

After `./llm-local train mlflow up`, open `http://localhost:15000`.
