# Exec Plan — US-010 Manifest-driven Agent conversation trainer

## Goal

Connect `dataset_manifest.json` and Agent conversation JSONL to Unsloth SFT so
changing DVC-tracked data changes what the Agent model learns.

## Scope

In scope:

- Replace hardcoded sample text in `training/unsloth/scripts/finetune_lora.py` with
  manifest-driven conversation loader (US-009 schema).
- Render `messages` arrays to SFT `text` for `SFTTrainer`.
- Propagate US-009 validation failures to train stage.
- MLflow params: `dataset_id`, row counts.

Out of scope:

- CV/VLM, 8k images, YOLO scripts
- W&B, production promotion automation

## Risk Classification

Risk flags: data model, existing behavior, weak proof.

Domain decision: **resolved** — Agent LLM conversation only.

## Work Phases

1. Implement conversation loader + unit tests (fixtures from US-009).
2. Wire loader in `finetune_lora.py`; extend `ct_train_config.json`.
3. Update simulate path to honor manifest row metadata.
4. GPU platform proof on fixture data (MinIO dev stack).

## Pause for human confirmation if:

- Tool-call / multi-agent JSONL formats exceed v1 `messages` schema.
