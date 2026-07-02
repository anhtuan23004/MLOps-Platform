# Spec Intake — Brooks-Lint DVC / Continuous Training Audit

Date: 2026-07-02

## Source

- User prompt: Brooks-Lint architecture audit (mode: Architecture Audit)
- External references:
  - PDF workflow (CV/YOLO/heatmap, DVC + S3, git commit inside stages)
  - `MLOps.doc` task list (8k images, W&B, SSH GPU setup)

## Classification

| Field | Value |
| --- | --- |
| Input type | New initiative (partial adoption of external docs) |
| Lane | high-risk |
| Initiatives | M02-artifact-lineage, M05-continuous-training |
| Health score | 69/100 (compatibility only; not implementation quality) |

## Risk flags

- Data model — dataset snapshot/delta contract, manifest schema
- External systems — S3/MinIO remote, DVC pull/push
- Existing behavior — trainer currently ignores real dataset content
- Weak proof — no integration test exercises real `dvc repro` + remote I/O
- Multi-domain — data lineage (M02) and training pipeline (M05)

## Restated work

External docs are **reference inputs**, not drop-in implementations. Adopt in
three bounded stories:

1. Harden DVC subproject + S3 remote with real repro/pull/push proof.
2. Define dataset snapshot contract for **Agent LLM conversation** data (JSONL).
3. Wire manifest-driven conversation loader into `finetune_lora.py` / Unsloth path.

## Brooks-Lint findings (accepted)

### Critical — domain model distortion

`prepare_data` writes checksum/manifest only; `finetune_lora.py` still trains on
fixed sample text. Pushing conversation data through current DVC will not change
training until a manifest-driven loader exists.

### Warning — adopt selectively from PDF

| Keep / adapt | Reject as-is |
| --- | --- |
| DVC + S3/MinIO, pull/push/status/dag | Hard-coded credentials in shell |
| Dataset naming/version metadata | `git commit` / `git tag` / `git push` inside DVC stages |
| AWS profile/env credentials | YOLO/heatmap scripts in LLM pipeline |
| Dataset validation (if CV confirmed) | DVC as model registry |
| | New `dvc/...` tree; repo uses `training/pipeline/` |
| | W&B (conflicts with ADR-002 MLflow role) |

### Architecture guardrails (ADR-002)

- DVC → dataset snapshots + pipeline stages under `training/pipeline/`
- MLflow → runs, checkpoints, model versions
- Release registry → promotion handoff
- Do not add W&B or DVC model registry without a new ADR

## Workspace validation (2026-07-02)

Findings re-checked on `/home/dev/MLOps-Platform`:

| Review claim | Current workspace |
| --- | --- |
| `.dvc/` empty | **Stale** — `training/pipeline/.dvc/` has `config`, cache, tmp |
| No `dvc.lock` | **Stale** — `training/pipeline/dvc.lock` exists |
| No `dvc` command | **Stale** — `.venv/bin/dvc` 3.67.1 available |
| Sequential fallback when DVC missing | **Still valid** — `llm_local/pipeline/runner.py` lines 109–116 |
| Trainer uses sample text | **Still valid** — `training/unsloth/scripts/finetune_lora.py` lines 86–91 |
| No real DVC integration test | **Still valid** — tests use stage modules / dry-run, not `dvc repro` + remote |
| US-003 platform proof with `dvc repro` | **Exists** — story evidence 2026-06-29; not CI-gated |

Pipeline tests: 9 passed (`test_training_pipeline.py`, `test_us004_train.py`).

## MLOps.doc task applicability

| Task | Verdict |
| --- | --- |
| Push legacy + 8k images to bucket | **Out of scope** — no 8k batch; Agent LLM JSONL only |
| Push Agent conversation dataset to bucket | Yes, with snapshot contract (US-009) |
| Co-locate training code with data pipeline | Already at `training/pipeline/dvc.yaml`; needs real loader (US-010) |
| Checkpoint/best weight by version | Yes via MLflow + DVC dataset ID + release record |
| Configure W&B | Defer — conflicts with ADR-002 |
| SSH GPU + manual library install | Prefer Docker/runbook over host installs |

## Story packets created

| Story | Title |
| --- | --- |
| [US-008](../stories/epics/E02-continuous-training/US-008-dvc-s3-remote-hardening/) | DVC subproject + S3 remote hardening |
| [US-009](../stories/epics/E04-artifact-lineage/US-009-dataset-snapshot-contract/) | Agent conversation dataset contract |
| [US-010](../stories/epics/E02-continuous-training/US-010-manifest-driven-trainer/) | Manifest-driven trainer integration |

## Decisions (confirmed 2026-07-02)

| Question | Answer |
| --- | --- |
| Problem domain | **LLM text/conversation for Agent** — not CV/VLM |
| 8k image batch | **None** — MLOps.doc 8k task is out of scope |
| Storage rollout | **MinIO dev first** for DVC/MLflow proof; document **production S3 bucket** separately (same prefix layout, no `AWS_ENDPOINT_URL`) |

Implications:

- US-009 schema: `conversation-json` / JSONL splits (`train.jsonl`, `val.jsonl`).
- US-010: extend Unsloth `finetune_lora.py` only — no CV/YOLO pipeline.
- US-008: platform proof targets local MinIO (`config/env/mlflow.env`); production
  bucket name/IAM left to operator (`config/dvc/config.local`).

## Harness delta

- Added intake record (this file)
- Added E04 epic + three high-risk story folders
- Updated `docs/stories/backlog.md` and `docs/TEST_MATRIX.md` (planned rows)
- Recorded human decisions (Agent LLM, no 8k, MinIO dev + S3 prod docs)
