# Design — US-008 DVC subproject + S3 remote hardening

## Domain Model

| Entity | Role |
| --- | --- |
| DVC subproject | `training/pipeline/` with own `.dvc/` metadata |
| S3 remote | `s3://<bucket>/dvc-storage` per `config/dvc/config.example` |
| Stage outputs | Manifest, run manifest, eval report, release pointer |

## Application Flow

```text
Operator sets AWS_* + MLFLOW_TRACKING_URI
  → ./llm-local train pipeline repro
  → runner.ensure_dvc_repo_layout()
  → dvc repro (cwd=training/pipeline)
  → optional dvc push after repro
```

Sequential fallback remains for dev machines without DVC installed but must not
be the only CI proof.

## Interface Contract

CLI unchanged: `./llm-local train pipeline {run|repro} [--dry-run]`.

New operator contract:

- Secrets in `training/pipeline/.dvc/config.local` (gitignored), not shell exports
  in repo scripts.
- Documented commands: `dvc pull`, `dvc push`, `dvc status`, `dvc dag`.

## Data Model

No schema migration. Lockfile `dvc.lock` tracks stage deps/outs; must be committed
when stage definitions change.

## UI / Platform Impact

CLI and CI only.

## Observability

Log when sequential fallback is used (`[!] dvc not installed` / `not initialized`).

## Alternatives Considered

1. **MLflow-only lineage** — rejected per ADR-002.
2. **Monorepo root DVC** — rejected; repo chose subdirectory layout.
3. **Git operations in register stage** — rejected (Brooks-Lint + release workflow).
