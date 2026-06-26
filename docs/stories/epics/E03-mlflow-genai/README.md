# E03 — MLflow GenAI integration

## Goal

Extend the existing MLflow + DVC continuous training path (US-003) with
[MLflow GenAI capabilities](http://mlflow.org/docs/latest/genai/): production
tracing, systematic LLM evaluation, and prompt versioning — without replacing
LiteLLM (gateway), DVC (data lineage), or the file-based release registry
(promotion).

## Scope

| In scope | Out of scope |
| --- | --- |
| MLflow Model Registry after real training | Replacing LiteLLM with MLflow AI Gateway |
| MLflow Tracing on serving requests | Replacing Prometheus/Grafana |
| MLflow GenAI Evaluation in `evaluate` stage | Replacing DVC |
| MLflow Prompt Registry for fine-tune templates | Full agent framework integration |

## Stories (implementation order)

| ID | Title | Depends on |
| --- | --- | --- |
| [US-004](US-004-gpu-train-model-registry.md) | Real Unsloth train + MLflow Model Registry | US-003 |
| [US-005](US-005-mlflow-serving-traces.md) | MLflow Tracing on LiteLLM/vLLM path | US-003, US-002 (serving up) |
| [US-006](US-006-mlflow-genai-eval-gate.md) | MLflow GenAI Evaluation as pipeline gate | US-004, US-005 (optional) |
| [US-007](US-007-mlflow-prompt-registry.md) | MLflow Prompt Registry for CT templates | US-004 |

## Product contract

- `docs/product/mlflow-genai.md`
- `docs/product/experiment-tracking.md` (classic tracking, extended by US-004)

## Architecture note

```text
DVC pipeline → train (MLflow run + registry) → evaluate (GenAI eval) → register (release draft)
Serving: Client → LiteLLM → vLLM (+ MLflow traces)
Prompts: MLflow Prompt Registry → train stage params
Promotion: release registry (unchanged)
```
