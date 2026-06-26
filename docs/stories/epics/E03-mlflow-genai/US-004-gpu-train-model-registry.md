# US-004 Real GPU training + MLflow Model Registry

## Status

planned

## Lane

normal

## Product Contract

Replace the dry-run stub in `llm_local/pipeline/stages/train.py` with a real
fine-tune path on the Unsloth GPU environment, and register the produced
artifact in **MLflow Model Registry**.

After this story:

- `train.dry_run: false` on a GPU VM produces real weights/adapters on disk and S3.
- MLflow run logs params, metrics, and artifacts; `mlflow.register_model` creates
  a version under `config/pipeline/params.yaml` → `model.name`.
- `run_manifest.json` includes `mlflow.model_uri` and registry version for the
  `register` stage and release registry lineage.

## Relevant Product Docs

- `docs/product/continuous-training.md`
- `docs/product/experiment-tracking.md`
- `docs/product/mlflow-genai.md`
- `docs/decisions/002-mlflow-dvc-s3-continuous-training.md`

## Acceptance Criteria

- `train.py` invokes Unsloth (container exec or documented script) when `dry_run` is false
- Successful train logs artifacts to MLflow S3 backend and calls `register_model`
- `dry_run: true` behavior unchanged for CI (`pytest`, `validate-quick`)
- `config/pipeline/params.yaml` documents train-related knobs (base model, epochs, adapter type)
- GPU VM proof documented in runbook or story evidence (full `dvc repro` without dry-run)
- TEST_MATRIX row US-004 added

## Design Notes

- Commands:
  - `./llm-local train up` — Unsloth environment
  - `./llm-local train mlflow up` — tracking server
  - `./llm-local train pipeline run` — with `CT_DRY_RUN=false` on GPU VM
- Prefer minimal wrapper: train stage shells to Unsloth workspace or calls a single
  entry script mounted from `training/unsloth/work/`.
- Do not auto-promote to prod; `register` stage still creates draft release only.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | pytest: dry-run train still passes; mock register_model path |
| Integration | compose + dvc.yaml valid; train stage with `CT_DRY_RUN=true` |
| Platform | Full `dvc repro` on GPU VM with S3 + MLflow; registered model visible in UI |
| Release | N/A (promotion remains US-002) |

## Harness Delta

- Update `docs/product/domains.md` — remove "stub/dry-run" for train stage
- Extend `docs/product/experiment-tracking.md` with Model Registry fields
- Optional: `docs/runbooks/continuous-training-gpu-vm.md`

## Evidence

<!-- evidence-metadata
validated_at:
host_type: gpu-runtime
gpu:
commands:
stale_when:
- train.py changes
- Unsloth image tag changes
- params.yaml model.base_model changes
-->

Pending GPU VM proof.
