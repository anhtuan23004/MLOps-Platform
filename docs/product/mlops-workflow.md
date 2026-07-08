# MLOps Workflow and Tech Stack

This is the visual operating flow for the current repo. It shows intended
handoffs, implemented stack choices, and the feedback loop without introducing a
separate workflow engine.

```mermaid
flowchart TB
  intent[Human intent or model change] --> intake[Feature intake + story packet<br/>docs/FEATURE_INTAKE.md<br/>docs/stories]
  intake --> config[Operator config<br/>config/platform.yaml<br/>runtime-catalog.yaml<br/>pipeline/params.yaml]

  subgraph data[Data preparation]
    raw[Raw JSONL splits<br/>training/pipeline/data/raw]
    dvc[DVC snapshot + remote<br/>MinIO dev / S3 prod]
    prepare[prepare_data<br/>Python stage]
    manifest[(dataset_manifest.json<br/>rows + checksums)]
    raw --> dvc --> prepare --> manifest
  end

  subgraph train[Model development]
    repro[dvc repro<br/>or sequential fallback]
    unsloth[Unsloth LoRA training<br/>GPU VM]
    mlflowRun[MLflow run<br/>params + metrics + artifacts]
    modelVersion[MLflow Model Registry<br/>lineage version]
    bundle[(adapter / checkpoint bundle)]
    repro --> unsloth
    unsloth --> mlflowRun --> modelVersion
    unsloth --> bundle
  end

  subgraph eval[Validation gates]
    evaluate[evaluate stage<br/>Python + evaluation scripts]
    publicTest[data/input structural inference]
    evalReport[(ct_eval_report.json<br/>predictions + metrics)]
    publicTest --> evaluate --> evalReport
  end

  subgraph release[Release and promotion]
    register[register stage]
    releaseRecord[(YAML release registry<br/>data/release-registry)]
    gates[submit / approve / promote]
    alias[dev / staging / prod aliases<br/>rollback pointer]
    register --> releaseRecord --> gates --> alias
  end

  subgraph serve[Serving runtime]
    inventory[Local model inventory<br/>models/registry.yaml]
    vllm[vLLM OpenAI API<br/>GPU runtime]
    litellm[LiteLLM gateway<br/>stable aliases]
    client[LLM clients]
    alias --> inventory --> vllm --> litellm --> client
  end

  subgraph observe[Observation and proof]
    prometheus[Prometheus metrics]
    grafana[Grafana dashboards]
    traces[MLflow GenAI traces<br/>LiteLLM to vLLM]
    matrix[docs/TEST_MATRIX.md<br/>validation evidence]
    vllm --> prometheus --> grafana
    litellm --> traces
    gates --> matrix
  end

  config --> repro
  manifest --> unsloth
  manifest --> register
  modelVersion --> register
  bundle --> register
  evalReport --> register
  grafana -.->|drift or regression| intake
```

## Stack by Stage

| Stage | Repo surface | Tech stack |
| --- | --- | --- |
| Harness intake | `docs/FEATURE_INTAKE.md`, `docs/stories/`, `docs/TEST_MATRIX.md` | Markdown contracts, Makefile validation ladder |
| Control plane | `llm_local/`, `./llm-local` | Python package + thin shell entrypoint, `uv` environment |
| Configuration | `config/` | YAML manifests, env templates, Docker Compose env files |
| Data versioning | `training/pipeline/data/`, `config/dvc/config.example` | DVC, JSONL manifests, MinIO for dev, S3 for prod |
| Training | `training/pipeline/`, `training/unsloth/` | DVC stages, Python stage modules, Unsloth, GPU VM |
| Experiment tracking | `training/mlflow/` | MLflow 3.x, Postgres metadata, S3-compatible artifact store |
| Evaluation | `evaluation/`, `llm_local/pipeline/stages/evaluate.py` | Python structural checks, benchmark scripts, optional lm-eval |
| Release registry | `llm_local/releases/`, `data/release-registry/` | YAML release records, aliases, audit log |
| Serving | `serving/vllm/`, `serving/litellm/` | vLLM OpenAI API runtime, LiteLLM gateway, Docker Compose |
| Observability | `observation/`, `config/mlflow-genai.yaml` | Prometheus, Grafana, optional GPU exporter, MLflow traces |

## Current Boundaries

- DVC is the workflow DAG for this phase; Airflow, Prefect, Kubeflow, and
  Kubernetes operators are not part of the current stack.
- MLflow tracks runs, artifacts, model versions, traces, and future GenAI eval;
  promotion still happens through the release registry.
- Serving promotion changes release metadata first. Runtime changes require
  `--apply-serving` or explicit config rendering.
