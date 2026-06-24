# Data Versioning (DVC) — MLOps-Platform

## Role

DVC tracks **dataset snapshots** and **pipeline reproducibility** for continuous
training. It is the source of truth for which data version produced which model.

## Remote storage

Production direction: **S3-compatible remote** (AWS S3 or MinIO).

Configure from `config/dvc/config.example` (copy to `training/pipeline/.dvc/config`):

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
