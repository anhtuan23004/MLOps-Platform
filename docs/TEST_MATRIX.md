# Test Matrix

This file maps product behavior to proof.

Rows marked `implemented` must link to story packets with recorded validation
evidence. Do not mark a row implemented until tests or validation evidence
exist.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built |
| implemented | Implemented and proof exists |
| changed | Contract changed after earlier implementation |
| retired | No longer part of the product contract |

## Matrix

| Story | Contract | Unit | Integration | E2E | Platform | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| US-001 | Model release lifecycle contract (stages + promotion direction) | no | no | no | no | planned | docs/stories/epics/E01-model-release-lifecycle/US-001-define-promotion-lifecycle.md |
| US-002 | Release registry CLI + promotion gates + serving apply | yes | yes | no | no | in_progress | docs/stories/epics/E01-model-release-lifecycle/US-002-release-registry-cli.md |
| US-003 | MLflow + DVC continuous training pipeline (S3) | yes | yes | no | no | in_progress | docs/stories/epics/E02-continuous-training/US-003-mlflow-dvc-pipeline.md |
| US-004 | Real GPU train + MLflow Model Registry | yes | yes | no | yes | in_progress | docs/stories/epics/E03-mlflow-genai/US-004-gpu-train-model-registry.md |
| US-005 | MLflow Tracing on LiteLLM/vLLM serving path | yes | yes | no | yes | in_progress | docs/stories/epics/E03-mlflow-genai/US-005-mlflow-serving-traces.md |
| US-006 | MLflow GenAI Evaluation as CT pipeline gate | yes | yes | no | yes | planned | docs/stories/epics/E03-mlflow-genai/US-006-mlflow-genai-eval-gate.md |
| US-007 | MLflow Prompt Registry for continuous training | yes | yes | no | no | planned | docs/stories/epics/E03-mlflow-genai/US-007-mlflow-prompt-registry.md |

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, service contracts, or command behavior.
- E2E proof covers user-visible browser or client flows.
- Platform proof covers deployment, GPU/runtime, shell, host, or infrastructure
  behavior that cannot be proven in lower layers.
- Production-ready claims require fresh release evidence with date, host,
  runtime, image/model identifiers, commands, and stale triggers.
