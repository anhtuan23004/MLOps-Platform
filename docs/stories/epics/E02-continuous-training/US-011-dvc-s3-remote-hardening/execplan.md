# Exec Plan — US-008 DVC subproject + S3 remote hardening

## Goal

Make `training/pipeline/` a fully initialized DVC subproject with committed
metadata, working S3/MinIO remote, and automated proof that `dvc pull`, `dvc push`,
`dvc status`, and `dvc repro` behave correctly — not only sequential module fallback.

## Scope

In scope:

- `dvc init --subdir` layout under `training/pipeline/` with committed `.dvc/config`
  template and lockfile discipline documented for operators.
- Integration test that runs real `dvc repro` (dry-run compatible stages) when DVC
  is available; fails clearly when remote credentials are missing in CI.
- Document operator steps for `config.local` secrets (no hard-coded credentials).
- Remove reliance on sequential fallback as the **only** proof path in CI.

Out of scope:

- Git commit/tag/push inside DVC stages (explicitly rejected per Brooks-Lint).
- DVC model registry.
- Uploading production customer datasets.

## Risk Classification

Risk flags:

- External systems (S3/MinIO)
- Existing behavior (US-003 pipeline runner fallback)
- Weak proof (no remote I/O test today)

Hard gates:

- External provider behavior (S3 remote)

## Work Phases

1. Audit current `training/pipeline/.dvc/` vs `dvc init --subdir` expectations.
2. Add integration test invoking `dvc repro` through the same entrypoint as CLI.
3. Add optional MinIO-backed test job or documented manual platform proof for push/pull.
4. Update `data-versioning.md` operator section.
5. Record evidence in story `validation.md`.

## Stop Conditions

Pause for human confirmation if:

- Production bucket name/IAM policy is undefined when moving past MinIO dev proof.
- CI cannot reach MinIO without documented secrets (use optional platform job).
