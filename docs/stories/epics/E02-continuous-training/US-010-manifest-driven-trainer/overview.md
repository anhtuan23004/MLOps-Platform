# Overview — US-010 Manifest-driven Agent conversation trainer

## Status

planned

## Lane

high-risk

## Domain decision (confirmed)

**LLM Agent conversation** via Unsloth SFT. CV/VLM and 8k image batch are out of scope.

## Current Behavior

- `train` stage passes `dataset_id` to MLflow and Unsloth config but
  `finetune_lora.py` trains on hardcoded sample text (see lines 86–91).

## Target Behavior

- Loader reads `train.jsonl` / `val.jsonl` from manifest split paths.
- Rows rendered to SFT `text` field for `SFTTrainer`.
- Changing `data/raw` or `version_tag` changes training content and metrics.
- `training_summary.json` includes `rows_loaded` and `dataset_id`.

## Depends on

- US-009 (conversation schema + manifest)
- US-008 recommended for end-to-end MinIO `dvc pull` proof

## Affected Product Docs

- `docs/product/continuous-training.md`
- `docs/product/data-versioning.md`

## Non-Goals

- CV/YOLO trainer, W&B, PDF git-in-stage scripts

## Intake reference

- `docs/intake/2026-07-02-brooks-lint-dvc-ct-audit.md`
