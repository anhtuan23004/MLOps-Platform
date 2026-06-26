# MLflow GenAI — MLOps-Platform

Product contract for integrating [MLflow Agents and LLMs](http://mlflow.org/docs/latest/genai/)
with the existing hybrid stack (DVC, release registry, vLLM, LiteLLM).

## Principles

1. **MLflow complements, does not replace** LiteLLM (gateway), DVC (data), or
   `data/release-registry/` (promotion).
2. **Classic MLflow** (runs, metrics, model registry) owns the training artifact
   line; **GenAI features** own trace, eval, and prompt lineage.
3. **Config** for MLflow GenAI lives under `config/mlflow-genai.yaml`.

## Capability map

| MLflow GenAI feature | Platform role | Primary story |
| --- | --- | --- |
| Experiment tracking + Model Registry | CT train stage, promotion input | US-004 |
| Tracing (OpenTelemetry) | Debug serving path LiteLLM → vLLM | US-005 |
| Evaluation (LLM judges) | `evaluate` stage quality gate | US-006 |
| Prompt management | Versioned fine-tune / chat templates | US-007 |

## Tracing (US-005)

Enable in `config/mlflow-genai.yaml`:

```yaml
genai:
  tracing_enabled: true
```

Then:

```bash
./llm-local train mlflow up    # tracking server on llm-net
./llm-local serve litellm up   # renders config/active/litellm-config.yaml + env
```

- Traces go to experiment `mlops-platform-serving-traces` (configurable).
- LiteLLM uses `success_callback: [mlflow]` when tracing is on.
- Prometheus metrics in `observation/` remain the SLO source.

## Evaluation (US-006)

- `evaluate` pipeline stage may call MLflow GenAI evaluation APIs.
- Input: dataset split from DVC `dataset_manifest.json`; target: promoted model
  endpoint or artifact from train stage.
- Output: `evaluation/results/ct_eval_report.json` with pass/fail and scorer
  breakdown; linked to MLflow run ID.
- Failed eval blocks `register` stage (same as `evaluate.min_accuracy` today).

## Prompt registry (US-007)

- Fine-tune prompt templates stored in MLflow Prompt Registry, not duplicated in
  git-only YAML.
- `config/pipeline/params.yaml` holds a reference URI/name@version only.
- Train stage resolves prompt before invoking Unsloth.

## Config (planned)

```yaml
# config/mlflow-genai.yaml (introduced with US-005)
mlflow:
  tracking_uri: http://localhost:15000
  experiments:
    continuous_training: mlops-platform-continuous-training
    serving_traces: mlops-platform-serving-traces
    evaluation: mlops-platform-eval
  genai:
    tracing_enabled: false
    eval_scorers:
      - relevance
      - hallucination
    prompt_name: fine-tune-chat
```

## Handoff to release registry

Unchanged from US-003: `register` stage writes a **draft** release with
`training_config_ref` containing MLflow run ID and (after US-004) registered
model name/version. Promotion still flows through `./llm-local release`.
