# Overview — US-009 Agent conversation dataset contract

## Status

planned

## Lane

high-risk

## Domain decision (confirmed)

**LLM text/conversation for Agent fine-tuning.** No CV/VLM path and no 8k image
batch from MLOps.doc.

## Current Behavior

- `prepare_data` hashes `data/raw/` and writes `dataset_manifest.json` with
  `dataset_id`, checksum, and placeholder train/val/test splits sharing one checksum.
- No validation of conversation JSONL schema, row counts, or required splits.
- Brooks-Lint PDF/MLOps.doc CV assumptions do not apply.

## Target Behavior

- Documented contract for Agent conversation snapshots under `data/raw/`.
- `prepare_data` fails fast on schema violations (missing files, invalid JSONL rows).
- Manifest includes lineage fields: `label_schema: conversation-json`, row counts,
  `version_tag`, full snapshot only (no delta batch in scope).
- Operator runbook: MinIO dev upload + DVC push; production bucket documented separately.

## Affected Users

- Data engineer curating Agent conversation exports
- ML engineer consuming `dataset_manifest.json`

## Affected Product Docs

- `docs/product/data-versioning.md` (dev MinIO + production bucket)
- `docs/product/continuous-training.md` (Agent dataset hook)

## Non-Goals

- 8k image upload or YOLO/heatmap validation
- W&B, SSH host library installs, git commit inside DVC stages
- CV/VLM trainer pipeline

## Intake reference

- `docs/intake/2026-07-02-brooks-lint-dvc-ct-audit.md`

## Depends on

- None (can start in parallel with US-008)

## Unblocks

- US-010 manifest-driven trainer
