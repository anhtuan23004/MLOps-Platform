# Story Backlog

Create story packets when work is selected, not before.

## Candidate Initiatives

| Initiative | Description | Status |
| --- | --- | --- |
| M01-model-release-lifecycle | Define candidate release metadata, evaluation gates, promotion, and rollback for model artifacts. | in_progress |
| M02-artifact-lineage | Define external artifact storage, checksums, dataset/config lineage, and cleanup policy. | in_progress |
| M03-serving-gateway | Stabilize promoted model serving through the vLLM runtime and LiteLLM gateway aliases, with deployment-neutral release bundles. | candidate |
| M04-production-observability | Define dashboards, alerts, runbooks, and evidence freshness for promoted models. | candidate |
| M05-continuous-training | MLflow + DVC pipeline on S3 with scheduled and data-driven retrain. | in_progress |
| M06-mlflow-genai | MLflow GenAI: model registry, tracing, eval gates, prompt registry. | planned |

## Next Selected Story

- [`US-008`](epics/E02-continuous-training/US-008-llm-dataset-loader.md) — Manifest-driven LLM dataset loader (in progress; GPU proof pending)
- [`US-011`](epics/E02-continuous-training/US-011-dvc-s3-remote-hardening/) — DVC + MinIO dev / S3 prod hardening (planned)
- [`US-003`](epics/E02-continuous-training/US-003-mlflow-dvc-pipeline.md) — MLflow + DVC continuous training (implemented)
- [`US-002`](epics/E01-model-release-lifecycle/US-002-release-registry-cli.md) — Release registry CLI + serving promotion (in_progress)

## Intake — Brooks-Lint audit (2026-07-02)

External PDF + `MLOps.doc` reviewed for DVC/CT compatibility. Health score 69/100.
See [`docs/intake/2026-07-02-brooks-lint-dvc-ct-audit.md`](../intake/2026-07-02-brooks-lint-dvc-ct-audit.md).

## Epic E01 — Model release lifecycle (in progress)

See [`epics/E01-model-release-lifecycle/README.md`](epics/E01-model-release-lifecycle/README.md).

| Story | Title | Status |
| --- | --- | --- |
| [US-001](epics/E01-model-release-lifecycle/US-001-define-promotion-lifecycle.md) | Define promotion lifecycle | planned |
| [US-002](epics/E01-model-release-lifecycle/US-002-release-registry-cli.md) | Release registry CLI + real serving promotion | in_progress |

## Epic E02 — Continuous training (in progress)

See [`epics/E02-continuous-training/README.md`](epics/E02-continuous-training/README.md).

| Story | Title | Status |
| --- | --- | --- |
| [US-003](epics/E02-continuous-training/US-003-mlflow-dvc-pipeline.md) | MLflow + DVC continuous training pipeline | implemented |
| [US-008](epics/E02-continuous-training/US-008-llm-dataset-loader.md) | Manifest-driven LLM dataset loader | in_progress |
| [US-011](epics/E02-continuous-training/US-011-dvc-s3-remote-hardening/) | DVC subproject + S3 remote hardening | planned |

## Epic E03 — MLflow GenAI (planned)

See [`epics/E03-mlflow-genai/README.md`](epics/E03-mlflow-genai/README.md).

| Story | Title | Status |
| --- | --- | --- |
| [US-004](epics/E03-mlflow-genai/US-004-gpu-train-model-registry.md) | Real GPU train + MLflow Model Registry | implemented |
| [US-005](epics/E03-mlflow-genai/US-005-mlflow-serving-traces.md) | MLflow Tracing on serving path | in_progress |
| [US-006](epics/E03-mlflow-genai/US-006-mlflow-genai-eval-gate.md) | MLflow GenAI Evaluation gate | planned |
| [US-007](epics/E03-mlflow-genai/US-007-mlflow-prompt-registry.md) | MLflow Prompt Registry | planned |

## Intake Notes

Before implementation, classify the request with `docs/FEATURE_INTAKE.md`,
locate affected product docs, create or update the story packet, and add a test
matrix row with expected proof.

## Superseded packets

US-009 and US-010 high-risk folders were superseded by US-008 (contract + loader combined).
