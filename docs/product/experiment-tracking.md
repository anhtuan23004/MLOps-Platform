# Experiment Tracking (MLflow) — MLOps-Platform

## Role

MLflow tracks **training runs**, **parameters**, **metrics**, and **model artifacts**
for continuous training and promotion decisions.

## Tracking server

Docker Compose: `training/mlflow/docker-compose.yml`

Default tracking URI: `http://localhost:15000` (override with `MLFLOW_TRACKING_URI`).

Runtime image: `dhi.io/mlflow:3` (Docker Hardened Images). The service uses the
image entrypoint directly, so the compose command is `server ...` rather than
`mlflow server ...`.

## Local dev vs production

| Concern | Local dev (`./llm-local train mlflow up`) | Production (release / CI-CD) |
| --- | --- | --- |
| Metadata backend | Postgres in compose (`postgres` service) | External managed Postgres |
| Artifact store | MinIO in compose (`minio` service) | AWS S3 |
| Credentials | `config/env/mlflow.env` (from example) | IAM / secrets from release pipeline |
| DVC remote | Same MinIO bucket, `s3://<bucket>/dvc-storage` | S3 bucket from infra |

Local stack services: **Postgres** (metadata), **MinIO** (artifacts + shared bucket
for DVC), **MLflow** (tracking UI + registry). `minio-init` creates the artifact
bucket on first start.

MinIO console (dev): `http://localhost:19001` (default; see `MINIO_CONSOLE_PORT`).

## Artifact storage

Artifacts stored in **S3-compatible storage** (`MLFLOW_ARTIFACT_ROOT`, typically
backed by `MLFLOW_S3_BUCKET`). Metadata uses **Postgres** via
`MLFLOW_BACKEND_STORE_URI` in the local dev stack.

Environment:

| Variable | Purpose |
| --- | --- |
| `MLFLOW_TRACKING_URI` | Client + pipeline target |
| `MLFLOW_BACKEND_STORE_URI` | Metadata backend (`postgresql://…@postgres:5432/…` in dev) |
| `MLFLOW_S3_BUCKET` | S3 bucket for artifacts (and DVC remote prefix in dev) |
| `MLFLOW_ARTIFACT_ROOT` | Artifact destination URI |
| `AWS_*` | S3 credentials (MinIO in dev, AWS IAM in prod) |
| `AWS_ENDPOINT_URL` | MinIO endpoint; `http://minio:9000` in compose, `http://localhost:<MINIO_HOST_PORT>` on host |
| `MINIO_*` | MinIO root user/password and host ports (dev only) |
| `POSTGRES_*` | Postgres credentials for local metadata store (dev only) |

**Host-side pipeline / DVC**: export `AWS_ENDPOINT_URL=http://localhost:19000`
(or your `MINIO_HOST_PORT`) so clients reach MinIO from outside the compose network.

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
