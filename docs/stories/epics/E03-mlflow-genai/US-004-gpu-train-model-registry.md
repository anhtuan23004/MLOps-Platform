# US-004 Real GPU training + MLflow Model Registry

## Status

implemented

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
- Local MLflow stack now builds a wrapper image around `dhi.io/mlflow:3` with
  `boto3` installed so S3/MinIO artifact logging works in dev

## Evidence

<!-- evidence-metadata
validated_at: 2026-06-29
host_type: local GPU host
gpu: NVIDIA GeForce RTX 3060
commands:
- .venv/bin/python -m pytest tests/test_training_pipeline.py tests/test_us004_train.py -q
- make validate-quick
- make test-integration
- docker compose -f training/mlflow/docker-compose.yml build mlflow
- ./llm-local train mlflow up
- docker exec mlflow-mlflow-1 python -c 'import boto3; print(boto3.__version__)'
- docker exec unsloth python /workspace/scripts/finetune_lora.py /workspace/work/ct_train_config.json
- cd training/pipeline && MLFLOW_TRACKING_URI=http://localhost:15000 AWS_ACCESS_KEY_ID=mlops AWS_SECRET_ACCESS_KEY=mlops-secret AWS_DEFAULT_REGION=us-east-1 AWS_ENDPOINT_URL=http://localhost:19000 CT_DRY_RUN=false RELEASE_REGISTRY_ROOT=/home/dev/MLOps-Platform/training/pipeline/.state/release-registry ../../.venv/bin/dvc repro -f
- CT_DRY_RUN=false UNSLOTH_TRAIN_SIMULATE=1 MLFLOW_TRACKING_URI=http://localhost:15000 ./llm-local train pipeline run
stale_when:
- train.py changes
- unsloth_runner.py changes
- finetune_lora.py changes
- mlflow_registry.py changes
- runner.py changes
- training/mlflow/Dockerfile changes
- training/mlflow/docker-compose.yml changes
-->

Local proof (2026-06-27): pytest 5/5 passed for pipeline dry-run plus US-004
simulate/register mocks. `make validate-quick` passed 29/29 and `make
test-integration` passed 32/32. GPU VM full repro remains pending in
`docs/runbooks/continuous-training-gpu-vm.md`.

Local MLflow stack fix (2026-06-27): built `mlops-platform/mlflow:3-boto3`
from `training/mlflow/Dockerfile`, restarted `./llm-local train mlflow up`, and
verified `docker exec mlflow-mlflow-1 python -c 'import boto3; print(boto3.__version__)'`
returns `1.43.36`. This clears the missing-`boto3` blocker for S3/MinIO artifact
logging in local dev.

Local simulated end-to-end proof (2026-06-27): `CT_DRY_RUN=false
UNSLOTH_TRAIN_SIMULATE=1 MLFLOW_TRACKING_URI=http://localhost:15000 ./llm-local
train pipeline run` completed successfully via sequential fallback. MLflow
registered `mlops-ct-model` version `2`, `training/pipeline/models/artifacts/run_manifest.json`
recorded `model_uri=models:/mlops-ct-model/2`, and register stage created draft
release `rel-ct-605c91bf` under pipeline-local fallback registry
`training/pipeline/.state/release-registry/` because the default
`data/release-registry/*` subdirectories are root-owned in this workspace.

GPU VM proof (2026-06-29): real Unsloth fine-tune completed on NVIDIA GeForce
RTX 3060 without `UNSLOTH_TRAIN_SIMULATE`. A direct container smoke run via
`docker exec unsloth python /workspace/scripts/finetune_lora.py /workspace/work/ct_train_config.json`
completed with final loss `1.9987`. Full pipeline proof via `dvc repro -f`
then completed end-to-end with `CT_DRY_RUN=false`, producing adapter artifacts
under `training/pipeline/models/artifacts/staging/`, registering MLflow model
version `5` with run ID `d94c9b34507d4ee6a5251ee869fbe573`, and creating draft
release `rel-ct-8284218f` in the writable fallback registry
`training/pipeline/.state/release-registry/`.
