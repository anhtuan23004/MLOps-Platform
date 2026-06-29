# Data Versioning (DVC) — MLOps-Platform

## Role

DVC tracks **dataset snapshots** and **pipeline reproducibility** for continuous
training. It is the source of truth for which data version produced which model.

## Remote storage

Production direction: **S3-compatible remote** (AWS S3 in production; **MinIO** in
local dev via the MLflow compose stack — same bucket, different prefix).

The pipeline runner creates `training/pipeline/.dvc/config` from
`config/dvc/config.example` when the file is missing in a fresh environment.
After the first run, edit the copied file for the target bucket:

```ini
[core]
    remote = s3remote

['remote "s3remote"']
    url = s3://<bucket>/dvc-storage
```

Environment variables:

| Variable | Purpose |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | S3 access key |
| `AWS_SECRET_ACCESS_KEY` | S3 secret |
| `AWS_DEFAULT_REGION` | Region |
| `AWS_ENDPOINT_URL` | Optional; set for MinIO |

## Pipeline location

`training/pipeline/dvc.yaml` — stages: `prepare_data` → `train` → `evaluate` → `register`.

## Triggers

1. **Data-driven**: `dvc repro` when `data/raw/` or `config/pipeline/params.yaml` changes.
2. **Scheduled**: cron calls `./llm-local train pipeline run` (see continuous-training.md).

## Integration

- `prepare_data` writes `data/processed/dataset_manifest.json` with version ID + checksum.
- `register` stage passes dataset versions into the release registry (`llm_local/releases`).
