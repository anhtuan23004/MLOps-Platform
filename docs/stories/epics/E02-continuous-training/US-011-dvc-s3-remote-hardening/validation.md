# Validation — US-008 DVC subproject + S3 remote hardening

## Proof Strategy

Prove DVC is the real orchestrator and S3 remote configuration is operable, not
only that Python stage modules run in isolation.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | `dvc_available`, `ensure_dvc_repo_layout`, config template copy |
| Integration | `dvc repro` from `training/pipeline` with `CT_DRY_RUN=true` |
| Integration | `dvc status` clean after repro |
| Platform | `dvc push` + `dvc pull` against MinIO with test prefix (manual or CI job) |
| Logs/Audit | Fallback path emits warning when DVC unavailable |

## Fixtures

- Temp pipeline dir or isolated `tmp_path` with copied `dvc.yaml`
- MinIO from `training/mlflow/docker-compose.yml` for platform proof

## Commands

```text
.venv/bin/python -m pytest tests/test_training_pipeline.py -q
# After implementation:
cd training/pipeline && ../../.venv/bin/dvc repro
cd training/pipeline && ../../.venv/bin/dvc status
cd training/pipeline && ../../.venv/bin/dvc push
```

## Acceptance Evidence

TBD — record date, host, DVC version, remote URL, and command output after implementation.
