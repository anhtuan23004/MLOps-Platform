"""MLflow run logging and Model Registry registration for continuous training."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from llm_local.pipeline.stages.common import mlflow_tracking_uri


def log_training_run(
    params: dict[str, Any],
    manifest: dict[str, Any],
    *,
    dry_run: bool,
    artifact_dir: Path | None = None,
    train_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    train_cfg = params.get("train", {})
    model_cfg = params.get("model", {})
    experiment = str(train_cfg.get("experiment", "mlops-platform-continuous-training"))
    run_name = f"ct-{manifest['dataset_id']}"

    run_info: dict[str, Any] = {
        "experiment": experiment,
        "run_name": run_name,
        "dry_run": dry_run,
        "tracking_uri": mlflow_tracking_uri(),
    }

    metrics = train_metrics or {}
    loss = float(metrics.get("final_loss", 0.42))
    epochs = float(metrics.get("epochs", train_cfg.get("epochs", 1)))

    if dry_run:
        run_info["run_id"] = f"dry-{uuid.uuid4().hex[:12]}"
        run_info["metrics"] = {"loss": loss, "epochs": epochs}
        return run_info

    import mlflow
    from mlflow.tracking import MlflowClient

    registered_name = str(model_cfg.get("name", "mlops-ct-model"))
    tracking_uri = mlflow_tracking_uri()
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)

    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(
            {
                "base_model": model_cfg.get("base_model"),
                "epochs": train_cfg.get("epochs"),
                "learning_rate": train_cfg.get("learning_rate"),
                "adapter_type": train_cfg.get("adapter_type", "lora"),
                "max_seq_length": train_cfg.get("max_seq_length", 2048),
                "batch_size": train_cfg.get("batch_size", 2),
                "dataset_id": manifest["dataset_id"],
            }
        )
        mlflow.log_metric("loss", loss)
        mlflow.log_metric("epochs", epochs)

        if artifact_dir and artifact_dir.is_dir():
            mlflow.log_artifacts(str(artifact_dir), artifact_path="model")
        else:
            raise RuntimeError(f"artifact_dir missing for MLflow logging: {artifact_dir}")

        run_id = run.info.run_id
        model_uri = f"runs:/{run_id}/model"
        registered = mlflow.register_model(model_uri, registered_name)
        client = MlflowClient(tracking_uri=tracking_uri)
        client.set_registered_model_alias(registered_name, "staging", registered.version)

        run_info.update(
            {
                "run_id": run_id,
                "model_name": registered_name,
                "model_version": int(registered.version),
                "model_uri": f"models:/{registered_name}/{registered.version}",
                "registered_model_uri": model_uri,
                "metrics": {"loss": loss, "epochs": epochs},
            }
        )
    return run_info
