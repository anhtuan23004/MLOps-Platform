# Exec Plan — US-009 Agent conversation dataset contract

## Goal

Define and implement the dataset contract for **Agent LLM conversation** fine-tuning:
JSONL layout, validation, manifest schema, and operator runbook for MinIO dev then
production S3.

## Scope

In scope:

- Product/schema doc for `train.jsonl` / `val.jsonl` under `data/raw/`.
- `prepare_data` validation (row counts, JSONL schema, non-empty splits).
- Manifest fields consumed by US-010 (`label_schema`, split paths, row counts).
- Runbook: MinIO dev `dvc push`; production bucket section in product docs.

Out of scope:

- 8k image batch or any CV/YOLO assets from external docs.
- Trainer loader implementation (US-010).
- W&B.

## Risk Classification

Risk flags: data model, external systems (S3), weak proof.

Hard gates: external provider (bucket upload).

## Work Phases

1. Finalize JSONL schema and manifest fields (this design doc).
2. Implement validator in `prepare_data` or `llm_local/pipeline/dataset/`.
3. Add unit tests with minimal Agent conversation fixtures.
4. Document MinIO dev + production bucket in `data-versioning.md`.
5. Operator smoke: push fixture snapshot to MinIO dev.

## Stop Conditions

Pause if Agent conversation schema needs tool-call / multi-agent formats not covered
by v1 `messages` array.
