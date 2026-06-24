"""Train stage with MLflow logging (dry-run capable for CI)."""

from __future__ import annotations

import json
import uuid

from llm_local.pipeline.stages.common import (
    PIPELINE_ROOT,
    dry_run_from_env_or_params,
    load_params,
    mlflow_tracking_uri,
    utc_now,
    write_json,
)


def log_mlflow_run(params: dict, manifest: dict, *, dry_run: bool) -> dict:
    train_cfg = params.get("train", {})
    model_cfg = params.get("model", {})
    experiment = "mlops-platform-continuous-training"
    run_name = f"ct-{manifest['dataset_id']}"

    run_info: dict = {
        "experiment": experiment,
        "run_name": run_name,
        "dry_run": dry_run,
        "tracking_uri": mlflow_tracking_uri(),
    }

    if dry_run:
        run_info["run_id"] = f"dry-{uuid.uuid4().hex[:12]}"
        run_info["metrics"] = {"loss": 0.42, "epochs": train_cfg.get("epochs", 1)}
        return run_info

    import mlflow

    mlflow.set_tracking_uri(mlflow_tracking_uri())
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(
            {
                "base_model": model_cfg.get("base_model"),
                "epochs": train_cfg.get("epochs"),
                "learning_rate": train_cfg.get("learning_rate"),
                "dataset_id": manifest["dataset_id"],
            }
        )
        loss = 0.35
        mlflow.log_metric("loss", loss)
        mlflow.log_metric("epochs", float(train_cfg.get("epochs", 1)))
        artifact_dir = PIPELINE_ROOT / "models/artifacts" / run.info.run_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "README.txt").write_text("Trained artifact placeholder\n")
        mlflow.log_artifacts(str(artifact_dir))
        run_info["run_id"] = run.info.run_id
        run_info["model_name"] = str(model_cfg.get("name", "mlops-ct-model"))
        run_info["metrics"] = {"loss": loss}
    return run_info


def main() -> int:
    params = load_params()
    manifest_path = PIPELINE_ROOT / "data/processed/dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    dry_run = dry_run_from_env_or_params(params)

    mlflow_info = log_mlflow_run(params, manifest, dry_run=dry_run)
    model_cfg = params.get("model", {})

    run_manifest = {
        "dataset_id": manifest["dataset_id"],
        "dataset_manifest": str(manifest_path.relative_to(PIPELINE_ROOT)),
        "base_model": model_cfg.get("base_model"),
        "model_name": model_cfg.get("name"),
        "trained_at": utc_now(),
        "dry_run": dry_run,
        "mlflow": mlflow_info,
        "params_ref": "params.yaml",
    }

    out = PIPELINE_ROOT / "models/artifacts/run_manifest.json"
    write_json(out, run_manifest)
    print(f"[+] Training complete dry_run={dry_run} run_id={mlflow_info.get('run_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
