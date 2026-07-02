# Training Scripts

| Script | Role |
| --- | --- |
| `finetune_lora.py` | US-004 Unsloth LoRA entrypoint (runs inside `unsloth` container) |

Invoked by `llm_local/pipeline/unsloth_runner.py` via `docker exec` when
`train.dry_run` is false.

Config is written to `training/unsloth/work/ct_train_config.json` and artifacts
land in `training/pipeline/models/artifacts/staging/` (pipeline volume mount).
