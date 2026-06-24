# Model Release Lifecycle (Stages + Promotion) — MLOps-Platform

This document defines the **stage taxonomy** and the repo's **promotion direction**.
It is a product contract: it describes intended behavior and required evidence,
even if the underlying automation is not implemented yet.

## What "promotion" means here

Promotion is a **controlled change of which model release is exposed** through the
serving surfaces (vLLM runtime + LiteLLM gateway aliases), backed by durable
release metadata, reproducible lineage, and measurable gates. Promotion must
always preserve a **rollback target**.

Promotion is not "deploying code". It is "advancing a model release" from a
candidate state to a more trusted serving state.

## Stage taxonomy (end-to-end)

### 1) Data preparation

Goal: produce a dataset snapshot suitable for training and evaluation, with
lineage and replayability.

Required outputs (intended):
- Dataset **collection** and ingestion notes.
- **Cleaning** and quality checks (schema, missingness, dedupe).
- **Labeling** (if applicable) and labeling QA.
- **Feature engineering** definition (or prompt formatting templates for LLMs).
- **Dataset versioning** (ID, checksum, and where the snapshot lives).

Evidence examples:
- Dataset manifest: dataset ID, time range, checksum, storage URI.
- Data QA report: counts, schema drift checks, label distribution.

### 2) Model development

Goal: produce a reproducible model artifact from a declared config.

Scope:
- Training / fine-tuning (or conversion) runs.
- Experiment tracking (runs, configs, metrics, artifacts).
- Hyperparameter tuning (if used).

Required outputs (intended):
- Training configuration + code version reference.
- Produced artifacts: checkpoints/adapters/converted weights.
- Run metadata: hardware, runtime versions, seeds.

Evidence examples:
- Run record: config, metrics, artifact IDs, reproducibility notes.

### 3) Validation (pre-promotion gates)

Goal: decide whether a release is eligible to be promoted.

Validation categories (intended):
- **Offline metrics** on a held-out test set (task quality).
- **Bias / safety checks** where relevant for the product domain.
- **Runtime compatibility** (loads, tokenization, max context, quantization).
- **Performance** (latency/throughput/memory) against a baseline.

Required outputs (intended):
- Evaluation report (metrics + methodology + dataset versions).
- Baseline comparison (what changed, why it’s acceptable).
- Registry entry created or updated for the release candidate.

Evidence examples:
- `evaluation/` output bundle (metrics JSON + report markdown).
- Load test results for vLLM runtime on the target host class.

### 4) Deployment (serving + controlled rollout)

Goal: publish a release in a way that is safe to consume and easy to roll back.

Deployment modes (intended):
- **Batch** inference jobs.
- **Online** serving (vLLM runtime), surfaced via LiteLLM aliases.

CI/CD surface (intended):
- Promotion is a workflow step with explicit inputs/outputs, not a manual edit.

Canary/rollback (intended):
- Canary duration and traffic slice are explicit.
- Rollback procedure is always available and tested.

Evidence examples:
- Serving bundle: runtime config + gateway routing + model artifact pointers.
- Canary report: error rate, latency deltas, sample quality spot-check.

### 5) Monitoring (post-promotion)

Goal: detect regressions and trigger retraining or rollback fast.

Monitoring categories (intended):
- **Data drift** (input distribution change).
- **Model drift** (quality degradation signals).
- **Serving performance** (latency, throughput, errors, saturation).
- **Retraining triggers** (thresholds + owner + escalation path).

Evidence examples:
- Dashboards (Grafana) and alert rules (Prometheus).
- Runbooks and rollback triggers documented.

## Release artifacts (what must exist to promote)

At promotion time, a release should have a minimum set of durable artifacts.

### Release record (registry metadata)
Minimum fields (intended):
- `release_id` and human name
- `source_artifact` (base model or upstream ID)
- `dataset_versions` (train/val/test IDs + checksums)
- `training_config_ref` (path or immutable reference)
- `eval_report_ref` (path/URI)
- `serving_bundle_ref` (path/URI)
- `promotion_state` (see below)
- `rollback_to_release_id` (required once in staging/prod)
- `created_at`, `created_by`, `approved_by` (if approval is used)

### Serving bundle
Minimum contents (intended):
- vLLM runtime spec (model path, quantization, max context, GPU layout)
- Gateway routing spec (LiteLLM alias → release_id)
- Rollback pointer (previous release_id + procedure link)

## Promotion lifecycle (states + environments)

### States
These states are intentionally generic so the repo can stay hybrid (LLM-first,
extensible to other ML types).

- `draft`: WIP release record; may not be reproducible.
- `candidate`: complete lineage + validation run exists; eligible for review.
- `approved`: explicitly approved for exposure (human or policy-based).
- `promoted`: actively served via an alias in at least one environment.
- `retired`: no longer eligible for serving; kept for audit and rollback history.

### Environment mapping
Environment is the *where*; state is the *what*.

- `dev`: experimentation and internal dogfooding. Can serve `candidate`.
- `staging`: production-like. Must serve only `approved` or `promoted`.
- `prod`: external-facing. Must serve only `promoted` and must have rollback target.

## Canary and rollback rules (direction)

Canary (direction):
- Always compare canary metrics to the current stable release.
- Canary gates should include: error rate, p95 latency, and at least one quality proxy.
- Canary must have an explicit timebox and traffic slice.

Rollback (direction):
- Rollback is a first-class operation: switch alias back to `rollback_to_release_id`.
- Rollback must be possible without rebuilding artifacts.
- Rollback triggers are documented per environment (staging vs prod).

## Validation ladder hooks (harness integration)

This repo tracks proof via the harness ladder in `config/validation-commands.yaml`:
- `make validate-quick`
- `make test-integration`
- `make test-platform` (prepared host)
- `make release-check` (prepared host + selected models)

Promotion-related stories should specify which ladder steps are required and what
artifacts must be attached as evidence.

