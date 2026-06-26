# US-005 MLflow Tracing on serving path

## Status

planned

## Lane

normal

## Product Contract

Enable [MLflow Tracing](http://mlflow.org/docs/latest/genai/) for requests flowing
through **LiteLLM → vLLM**, so operators can inspect prompts, model responses, and
latency in the MLflow UI alongside Prometheus dashboards.

## Relevant Product Docs

- `docs/product/mlflow-genai.md`
- `docs/product/experiment-tracking.md`

## Acceptance Criteria

- `config/mlflow-genai.yaml` (or `config/platform.yaml` extension) defines tracing
  experiment name and enable flag
- Tracing can be toggled off for local dev (`tracing_enabled: false`)
- When enabled, sample requests through LiteLLM produce traces visible at
  `MLFLOW_TRACKING_URI` under experiment `mlops-platform-serving-traces`
- Documented setup: env vars in `config/env/litellm.env` and/or LiteLLM callback
- No regression to `./llm-local serve litellm up` when tracing disabled
- TEST_MATRIX row US-005 added

## Design Notes

- Use MLflow OpenTelemetry-compatible tracing SDK or LiteLLM integration where
  available; avoid duplicating Prometheus metrics.
- Traces are **debug/observability**; promotion gates still use eval + release registry.
- Optional CLI: `./llm-local observe traces {on|off}` — only if needed; prefer config flag.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Config load + tracing helper unit tests |
| Integration | Compose up with tracing disabled passes `validate-quick` |
| Platform | Manual: send chat request via LiteLLM; trace appears in MLflow UI |
| Release | N/A |

## Harness Delta

- Add `docs/product/mlflow-genai.md` tracing section (if not already complete)
- Update `docs/ARCHITECTURE.md` observation plane diagram

## Evidence

<!-- evidence-metadata
validated_at:
host_type: gpu-runtime
gpu:
commands:
- ./llm-local serve vllm up
- ./llm-local serve litellm up
- curl LiteLLM chat completion
stale_when:
- LiteLLM image tag changes
- mlflow-genai.yaml tracing config changes
-->

Pending platform proof.
