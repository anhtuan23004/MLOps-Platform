"""Train stage: Unsloth fine-tune + MLflow Model Registry (US-004)."""

from __future__ import annotations

import json

from llm_local.pipeline.mlflow_registry import log_training_run
from llm_local.pipeline.stages.common import (
    PIPELINE_ROOT,
    dry_run_from_env_or_params,
    load_params,
    utc_now,
    write_json,
)
from llm_local.pipeline.unsloth_runner import run_unsloth_training, sync_staging_artifacts


def main() -> int:
    params = load_params()
    manifest_path = PIPELINE_ROOT / "data/processed/dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    dry_run = dry_run_from_env_or_params(params)
    model_cfg = params.get("model", {})

    staging = PIPELINE_ROOT / "models" / "artifacts" / "staging"
    train_metrics: dict = {}

    if dry_run:
        train_metrics = {"final_loss": 0.42, "epochs": params.get("train", {}).get("epochs", 1)}
    else:
        train_result = run_unsloth_training(params, manifest, output_dir=staging)
        sync_staging_artifacts(staging)
        train_metrics = train_result

    mlflow_info = log_training_run(
        params,
        manifest,
        dry_run=dry_run,
        artifact_dir=staging if not dry_run else None,
        train_metrics=train_metrics,
    )

    run_manifest = {
        "dataset_id": manifest["dataset_id"],
        "dataset_manifest": str(manifest_path.relative_to(PIPELINE_ROOT)),
        "base_model": model_cfg.get("base_model"),
        "model_name": model_cfg.get("name"),
        "trained_at": utc_now(),
        "dry_run": dry_run,
        "adapter_type": params.get("train", {}).get("adapter_type", "lora"),
        "artifact_dir": None if dry_run else str(staging.relative_to(PIPELINE_ROOT)),
        "mlflow": mlflow_info,
        "params_ref": "config/pipeline/params.yaml",
    }

    out = PIPELINE_ROOT / "models" / "artifacts/run_manifest.json"
    write_json(out, run_manifest)
    print(
        f"[+] Training complete dry_run={dry_run} run_id={mlflow_info.get('run_id')} "
        f"model_uri={mlflow_info.get('model_uri', 'n/a')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
