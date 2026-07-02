# Validation — US-010 Manifest-driven trainer integration

## Proof Strategy

Prove training row count and content derive from fixture data, not hardcoded sample.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Loader reads JSONL fixture; row count matches |
| Unit | Loader fails when manifest points to missing path |
| Unit | `UNSLOTH_TRAIN_SIMULATE` records `dataset_id` from manifest |
| Integration | Train stage dry-run references manifest paths |
| Platform | Non-simulated short train on fixture; loss/metrics logged to MLflow |

## Fixtures

Shared with US-009 minimal datasets.

## Commands

```text
.venv/bin/python -m pytest tests/test_us004_train.py -q
RELEASE_REGISTRY_ROOT=/tmp/mlops-registry ./llm-local train pipeline run --dry-run
# Platform (after loader):
CT_DRY_RUN=false UNSLOTH_TRAIN_SIMULATE=0 ... dvc repro train
```

## Acceptance Evidence

TBD — include `training_summary.json` showing `rows_loaded > 0` from fixture, not sample text.

## Brooks-Lint remediation

Closes **Domain Model Distortion** critical finding when evidence is recorded.
