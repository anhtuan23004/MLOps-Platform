# E04 — Artifact lineage

## Goal

Define how **Agent conversation** datasets are snapshotted, validated, versioned,
and linked to training runs and release records. M02-artifact-lineage initiative.

**Out of scope:** CV/image batches (including MLOps.doc 8k task).

## Scope

| In scope | Out of scope |
| --- | --- |
| Dataset snapshot/delta contract and manifest schema | Feature store or drift detection |
| Validation rules per problem domain (CV vs LLM) | W&B or alternate experiment trackers |
| Checksum/lineage linkage to DVC and MLflow | Automated data deletion/retention policy (later) |

## Stories (implementation order)

| ID | Title | Depends on |
| --- | --- | --- |
| [US-009](US-009-dataset-snapshot-contract/) | Agent conversation dataset contract | US-003 (pipeline skeleton) |

## Product contract

- `docs/product/data-versioning.md` (extend when contract is accepted)
- `docs/decisions/002-mlflow-dvc-s3-continuous-training.md`

## Architecture note

```text
Raw data (S3) → DVC track → prepare_data manifest → train/evaluate
  → MLflow run (dataset_id) → release registry draft
```
