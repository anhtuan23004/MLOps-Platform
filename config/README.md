# Configuration — MLOps-Platform

All operator-managed settings are centralized here. Workload directories
(`serving/`, `training/`, `observation/`) keep Docker Compose and runtime
assets only.

## Layout

| Path | Purpose |
| --- | --- |
| `platform.yaml` | Manifest: paths to every config file and env profile |
| `runtime-catalog.yaml` | Services, images, ports, GPU policy, format→runtime map |
| `validation-commands.yaml` | Harness validation ladder commands |
| `models/desired-models.yaml` | Product intent — which models to hold |
| `models/presets.yaml` | Serving preset definitions |
| `pipeline/params.yaml` | Continuous training parameters (DVC-tracked) |
| `dvc/config.example` | S3 remote template for DVC |
| `litellm/config.yaml` | LiteLLM gateway routing config |
| `env/*.env.example` | Per-service environment templates |
| `env/*.env` | Local overrides (gitignored; copy from `.example`) |
| `active/serving.yaml` | Generated active preset state (gitignored) |

## Quick start

```bash
# Create local env files from templates
./llm-local config init

# Edit service settings
vim config/env/vllm.env
vim config/pipeline/params.yaml

# DVC remote (first time)
cp config/dvc/config.example training/pipeline/.dvc/config
```

## Rules

- **Source of truth** for tunable values: files under `config/`.
- **Generated state** (`config/env/*.env`, `config/active/`, `models/registry.yaml`)
  is local runtime state, not product contract.
- Docker Compose loads variables via `--env-file config/env/<profile>.env`.

See [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) for how config flows into
serving, training, and promotion.
