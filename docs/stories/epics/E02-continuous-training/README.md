# E02 — Continuous training

## Goal

Establish a reproducible continuous training path that combines DVC lineage,
MLflow tracking, and release-registry handoff without claiming production proof
before GPU-host validation exists.

## Scope

| In scope | Out of scope |
| --- | --- |
| DVC pipeline stages for prepare/train/evaluate/register | Kubernetes-native pipeline orchestration |
| MLflow tracking server with S3-compatible artifact storage | Automated production promotion |
| CLI wrappers for run, repro, and scheduling | Feature store or drift-triggered retraining |
| Draft release creation from pipeline outputs | Replacing release registry with MLflow deployment features |
| Manifest-backed LLM JSONL loading (US-008) | CV/image training pipelines |

## Stories (implementation order)

| ID | Title | Depends on |
| --- | --- | --- |
| [US-003](US-003-mlflow-dvc-pipeline.md) | MLflow + DVC continuous training pipeline | US-001, US-002 |
| [US-008](US-008-llm-dataset-loader.md) | Manifest-driven LLM dataset loader | US-003 |
| [US-011](US-011-dvc-s3-remote-hardening/) | DVC subproject + S3 remote hardening | US-003 |

## Product contract

- `docs/product/continuous-training.md`
- `docs/product/data-versioning.md`
- `docs/product/experiment-tracking.md`
- `docs/decisions/002-mlflow-dvc-s3-continuous-training.md`

## Architecture note

```text
Dataset or schedule trigger → DVC repro → MLflow run/artifacts
  → evaluate output → draft release record → later approval/promotion
```
