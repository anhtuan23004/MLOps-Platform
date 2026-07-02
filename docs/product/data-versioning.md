# Data Versioning (DVC) — MLOps-Platform

## Role

DVC tracks **dataset snapshots** and **pipeline reproducibility** for continuous
training. It is the source of truth for which data version produced which model.

For Agent fine-tuning, snapshots are **conversation JSONL** under
`training/pipeline/data/raw/` (see US-008).

## Remote storage — two environments

Use the same **key layout** in dev and production; only endpoint and credentials differ.

| | Dev (MinIO) | Production (AWS S3) |
| --- | --- | --- |
| When | Local proof, CI optional | GPU VM / scheduled retrain |
| Bucket | `mlops-platform` (default) | Operator-provisioned, e.g. `acme-mlops-prod` |
| DVC URL | `s3://mlops-platform/dvc-storage` | `s3://<prod-bucket>/dvc-storage` |
| Endpoint | `AWS_ENDPOINT_URL=http://localhost:19000` on host | **Unset** (native S3) |
| Credentials | `config/env/mlflow.env` defaults | IAM role or CI secrets |
| MLflow artifacts | Same bucket, MLflow prefix | Same bucket pattern |

### Dev setup (MinIO first)

1. Start stack: `./llm-local train mlflow up` (Postgres + MinIO + MLflow).
2. Copy env: `config/env/mlflow.env` (see `MINIO_HOST_PORT=19000`).
3. Initialize DVC config if missing (runner copies `config/dvc/config.example`).
4. **Host-side** pipeline / DVC clients:

```bash
export AWS_ACCESS_KEY_ID=mlops
export AWS_SECRET_ACCESS_KEY=mlops-secret
export AWS_DEFAULT_REGION=us-east-1
export AWS_ENDPOINT_URL=http://localhost:19000
```

5. Repro and push:

```bash
cd training/pipeline
../../.venv/bin/dvc repro
../../.venv/bin/dvc push
```

Secrets for MinIO belong in `config/env/mlflow.env` (gitignored copy) or shell env —
not in committed DVC stage scripts.

### Production setup (S3 bucket)

1. Provision S3 bucket + IAM policy (`s3:ListBucket`, `s3:GetObject`, `s3:PutObject`
   on `arn:aws:s3:::<bucket>/dvc-storage/*`).
2. Create `training/pipeline/.dvc/config.local` (gitignored):

```ini
['remote "s3remote"']
    url = s3://<prod-bucket>/dvc-storage
```

3. Export **only** `AWS_*` from IAM — do **not** set `AWS_ENDPOINT_URL`.
4. Same commands: `dvc pull` before repro on fresh hosts; `dvc push` after data changes.

MLflow production uses the same bucket for artifacts with a different prefix;
see `docs/product/experiment-tracking.md`.

## Config template

`config/dvc/config.example` — copied to `training/pipeline/.dvc/config` on first run.
Override bucket URL in `config.local` per environment.

## Pipeline location

`training/pipeline/dvc.yaml` — stages: `prepare_data` → `train` → `evaluate` → `register`.

## LLM dataset contract

`dataset.format` in `config/pipeline/params.yaml` selects one JSONL schema for all
splits:

- `text`: each non-empty line is `{"text": "..."}`.
- `conversation`: each line is
  `{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}`.

Conversation roles are `system`, `user`, and `assistant`. Every conversation must
contain both a user and assistant message and end with `assistant`. Optional
top-level `id` and `metadata` fields are preserved.

Required split mapping:

```yaml
dataset:
  source: data/raw
  version_tag: v1
  format: conversation
  splits:
    train: train.jsonl
    val: val.jsonl
    test: test.jsonl
```

`prepare_data` validates every row and records the relative path, row count, and
SHA-256 checksum for each split. The trainer reloads the declared `train` split
from the manifest and rejects missing, changed, or invalid data.

In dry-run mode (`train.dry_run: true` or `CT_DRY_RUN=true`), missing split files
are accepted with `rows: 0` and `checksum: empty` so the pipeline can run without
local JSONL.

## Triggers

1. **Data-driven**: `dvc repro` when `data/raw/` or `config/pipeline/params.yaml` changes.
2. **Scheduled**: cron calls `./llm-local train pipeline run` (see continuous-training.md).

## Integration

- `prepare_data` writes `data/processed/dataset_manifest.json` with schema, split
  paths, row counts, version ID, and checksums.
- `register` stage passes dataset versions into the release registry (`llm_local/releases`).
