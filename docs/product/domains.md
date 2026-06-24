# Product Domains — MLOps-Platform

This file is the living product contract. It starts as a placeholder and should
be updated only when an accepted story defines concrete behavior.

## Shared lifecycle contract

Promotion semantics, stage taxonomy, and minimum release artifacts are defined in:
- `docs/product/model-release-lifecycle.md`

Release registry schema, CLI, and serving integration are defined in:
- `docs/product/model-releases.md`

## Model Registry And Release Metadata

Intended role: track durable model intent, local inventory, candidate releases,
artifact lineage, compatibility, approval status, and rollback targets.

Open decisions:

- Artifact storage location and checksum policy (beyond local release files).
- Approval policy automation (human vs policy-based).

Next story slice:
- Artifact lineage checksums and external storage (M02).

## Training And Conversion

Intended role: produce model checkpoints, adapters, converted formats, and
training evidence from reproducible configs.

Contracts:
- `docs/product/data-versioning.md` (DVC)
- `docs/product/experiment-tracking.md` (MLflow)
- `docs/product/continuous-training.md` (pipeline + triggers)

Open decisions:

- Wire Unsloth GPU trainer into `train` stage (currently dry-run capable stub).
- Automated promote after eval gates pass.

Next story slice:
- Real fine-tune in `llm_local/pipeline/stages/train.py` calling Unsloth container.

## Evaluation

Intended role: benchmark latency, quality, task-specific metrics, schema
adherence, and runtime compatibility before promotion.

Open decisions:

- Default quality gates.
- Per-domain metric thresholds.
- Required evidence artifacts.

Next story slice:
- Define the default evaluation bundle and how it attaches to a release record.

## Serving And Gateway

Intended role: expose promoted models through a vLLM runtime and stable
LiteLLM aliases while preserving release-friendly routing.

Open decisions:

- Production alias policy.
- Runtime promotion targets.
- Rollback behavior.

Next story slice:
- Define the first serving bundle contract: alias policy, canary knobs, rollback pointer format.

## Observability And Operations

Intended role: monitor gateway health, vLLM runtime health, latency, errors,
resource usage, and release drift.

Open decisions:

- Required dashboards and alerts.
- Incident runbooks.
- Evidence freshness and release-check cadence.

Next story slice:
- Define the minimum monitoring signals and rollback triggers needed to call a release “promoted”.
