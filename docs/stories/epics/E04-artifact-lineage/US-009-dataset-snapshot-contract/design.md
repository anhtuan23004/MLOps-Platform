# Design — US-009 Agent conversation dataset contract

## Domain Model

| Entity | Description |
| --- | --- |
| Dataset snapshot | Immutable tree at `training/pipeline/data/raw/` tracked by DVC |
| Manifest | `data/processed/dataset_manifest.json` — train stage input |
| Conversation row | One JSON object per line in JSONL split files |

Snapshots are **full only** in v1 (no delta/increment batch).

### Manifest fields

```json
{
  "dataset_id": "ds-<version_tag>-<checksum12>",
  "version_tag": "agent-v1",
  "snapshot_kind": "full",
  "source_path": "data/raw",
  "checksum_sha256": "...",
  "label_schema": "conversation-json",
  "file_counts": { "train_rows": 1200, "val_rows": 150 },
  "parent_snapshot_id": null,
  "prepared_at": "ISO-8601",
  "splits": {
    "train": { "path": "data/raw/train.jsonl", "row_count": 1200 },
    "val": { "path": "data/raw/val.jsonl", "row_count": 150 }
  }
}
```

### JSONL row schema (Agent)

Each line is a JSON object. Minimum v1 shape:

```json
{
  "messages": [
    { "role": "system", "content": "You are a helpful agent." },
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

`prepare_data` validates: valid JSON per line, `messages` is non-empty array,
each message has `role` and `content`. Optional `tools` / `metadata` keys allowed
but ignored by v1 loader.

### SFT text rendering (for US-010)

Loader converts `messages` to a single `text` field using the base model chat
template or a documented fallback format (e.g. ChatML-style) consistent with
`TinyLlama-1.1B-Chat` and Unsloth SFT.

## Application Flow

```text
Curate train.jsonl + val.jsonl → place under data/raw/
  → dvc add/track → dvc push (MinIO dev)
  → prepare_data validates → manifest → train (US-010)
```

## Interface Contract

- Input: `config/pipeline/params.yaml` — `dataset.source`, `dataset.version_tag`
- Output: `data/processed/dataset_manifest.json`
- Errors: missing split file, zero rows, malformed JSONL, empty `messages`

## Data layout

```text
training/pipeline/data/raw/
  train.jsonl
  val.jsonl
  README.md          # optional operator notes
```

## Remote storage

| Environment | Bucket / endpoint | DVC remote URL |
| --- | --- | --- |
| Dev (MinIO) | `mlops-platform` @ `localhost:19000` | `s3://mlops-platform/dvc-storage` + `AWS_ENDPOINT_URL` |
| Production (AWS S3) | Operator-provisioned bucket | `s3://<prod-bucket>/dvc-storage` — no endpoint override |

See `docs/product/data-versioning.md` and `config/env/mlflow.env`.

## Observability

Log `dataset_id`, row counts, validation duration in `prepare_data`.

## Alternatives Considered

1. **CV/YOLO layout from PDF** — rejected; domain is Agent LLM.
2. **8k delta snapshot** — rejected; not in scope.
3. **W&B artifact store** — rejected per ADR-002.
