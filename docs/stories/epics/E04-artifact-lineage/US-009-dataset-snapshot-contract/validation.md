# Validation — US-009 Agent conversation dataset contract

## Proof Strategy

Unit tests with minimal Agent JSONL fixtures. Platform proof uses MinIO dev bucket.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Valid `train.jsonl` + `val.jsonl` pass validation |
| Unit | Malformed JSON line fails with line number |
| Unit | Empty `messages` array fails |
| Unit | Missing `val.jsonl` fails (or documented optional — default: required) |
| Unit | Deterministic `dataset_id` for same tree |
| Integration | `prepare_data` via `run_stage.sh` with fixture |
| Platform | `dvc push` fixture to MinIO dev; `dvc pull` on clean tree |

## Fixtures

```text
tests/fixtures/datasets/agent-minimal/
  train.jsonl   # 2–3 conversation rows
  val.jsonl     # 1 row
```

## Commands

```text
.venv/bin/python -m pytest tests/ -k prepare_data -q
./llm-local train mlflow up
export AWS_ENDPOINT_URL=http://localhost:19000  # host-side DVC
cd training/pipeline && ../../.venv/bin/dvc push
```

## Acceptance Evidence

TBD — attach sample manifest and MinIO dev push confirmation.
