# US-006 MLflow GenAI Evaluation as pipeline gate

## Status

planned

## Lane

normal

## Product Contract

Replace the stub quality check in `llm_local/pipeline/stages/evaluate.py` with
[MLflow GenAI Evaluation](http://mlflow.org/docs/latest/genai/) where appropriate,
using DVC dataset lineage and blocking `register` when eval fails.

## Relevant Product Docs

- `docs/product/mlflow-genai.md`
- `docs/product/continuous-training.md`
- `docs/product/model-release-lifecycle.md` (validation stage)

## Acceptance Criteria

- `evaluate.py` runs MLflow eval (or documents hybrid: MLflow eval + existing
  `evaluation/` benchmarks for latency)
- Eval dataset derived from `dataset_manifest.json` (hold-out / test split)
- `evaluation/results/ct_eval_report.json` includes scorer results and MLflow eval run ID
- `evaluate.min_accuracy` (or new `evaluate.min_score`) gates pipeline; failed eval
  exits non-zero so DVC does not run `register`
- Dry-run mode produces deterministic stub report for CI
- `attach-eval` on release registry can reference the same report path
- TEST_MATRIX row US-006 added

## Design Notes

- Scorers (initial): relevance + hallucination (configurable in `config/mlflow-genai.yaml`)
- Eval target: vLLM OpenAI-compatible endpoint on `llm-net` or model artifact URI from US-004
- Keep `evaluation/scripts/` for throughput/lm-eval; this story owns **quality gate** in CT pipeline

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | pytest evaluate stage dry-run + fail gate logic |
| Integration | `train pipeline run --dry-run` full chain with eval pass |
| Platform | Eval against live vLLM model on GPU VM; MLflow eval UI shows run |
| Release | N/A |

## Harness Delta

- Update `docs/product/domains.md` evaluation section
- Link eval report schema in `docs/product/model-releases.md` if fields change

## Evidence

<!-- evidence-metadata
validated_at:
host_type:
gpu:
commands:
stale_when:
- evaluate.py changes
- eval scorer config changes
- test dataset version changes
-->

Pending.
