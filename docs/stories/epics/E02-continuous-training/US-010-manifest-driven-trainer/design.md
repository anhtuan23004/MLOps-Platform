# Design — US-010 Manifest-driven Agent conversation trainer

## Domain Model

Training consumes **Manifest** (US-009) + **JSONL splits** at `source_path`.

## Application Flow

```text
finetune_lora.py reads ct_train_config.json
  → load manifest
  → load_jsonl(splits.train.path)
  → render messages → text column
  → HuggingFace Dataset → SFTTrainer
```

`UNSLOTH_TRAIN_SIMULATE` still records `dataset_id`; optional fixture row count check.

## Interface Contract

`ct_train_config.json` additions:

```json
{
  "dataset_id": "ds-agent-v1-abc",
  "dataset_manifest": "/workspace/.../dataset_manifest.json",
  "source_path": "/workspace/pipeline/data/raw",
  "label_schema": "conversation-json"
}
```

## Data Model

Reuse US-009 manifest. Loader uses `splits.train.path` and optionally
`splits.val.path` for eval hooks later.

## Container mounts

Unsloth container must see `training/pipeline/data/raw` at the path in config
(existing pipeline volume mounts).

## Observability

- `training_summary.json`: `rows_loaded`, `dataset_id`, `label_schema`
- MLflow params: `dataset_id`, `dataset_checksum`, `train_rows`

## Alternatives Considered

1. **CV trainer branch** — rejected; domain is Agent LLM only.
2. **Permanent sample-text fallback** — rejected except explicit
   `CT_ALLOW_SAMPLE_DATA=true` for smoke tests.
