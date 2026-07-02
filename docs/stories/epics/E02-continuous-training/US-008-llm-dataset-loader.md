# US-008 Manifest-driven LLM dataset loader

## Status

in_progress

## Lane

normal

## Product Contract

Continuous training consumes validated LLM SFT data declared by the DVC dataset
manifest instead of synthetic rows embedded in the trainer.

## Relevant Product Docs

- `docs/product/data-versioning.md`
- `docs/product/continuous-training.md`

## Acceptance Criteria

- JSONL supports one configured format: `text` or `conversation`.
- `prepare_data` validates train/val/test and records path, row count, and checksum.
- Unsloth loads the train split from `dataset_manifest.json`.
- Training fails when rows are invalid or differ from the prepared manifest.
- Dry-run pipeline remains usable without local JSONL files.

## Design Notes

- `llm_local.pipeline.dataset` is shared by `prepare_data` and the mounted trainer.
- Conversation rows use Hugging Face `messages` with `role` and `content`.
- DVC owns dataset lineage; MLflow owns model artifacts and runs.
- `dvc.yaml` keeps `./run_stage.sh` for portable Python discovery (US-003).

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Schema, manifest, checksum, and container config tests |
| Integration | Dry-run pipeline and compose config |
| E2E | N/A |
| Platform | GPU fine-tune consumes a real manifest-backed dataset |
| Release | N/A |

## Harness Delta

- Supersedes planned US-009 (contract) and US-010 (loader) story packets.
- DVC remote hardening remains separate (US-011).

## Evidence

<!-- evidence-metadata
validated_at: 2026-07-02
host_type: local
gpu: none
commands:
- .venv/bin/python -m pytest tests/test_llm_dataset.py tests/test_training_pipeline.py tests/test_us004_train.py -q
- make validate-quick
- make test-integration
stale_when:
- llm_local/pipeline/dataset.py changes
- prepare_data.py changes
- finetune_lora.py changes
- dataset schema changes
-->

Local proof (2026-07-02): pytest 15/15 passed (`test_llm_dataset`, `test_training_pipeline`,
`test_us004_train`); `make validate-quick` 29/29 passed. GPU manifest consumption
remains pending on a host with Unsloth + real JSONL splits.
