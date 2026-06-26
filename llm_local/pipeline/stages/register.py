"""Register draft release from pipeline outputs into release registry."""

from __future__ import annotations

import json
import uuid

from llm_local.pipeline.stages.common import PIPELINE_ROOT, load_params, utc_now, write_json
from llm_local.releases.store import ReleaseStore


def main() -> int:
    params = load_params()
    prefix = str(params.get("register", {}).get("release_prefix", "rel-ct"))
    dataset_manifest = json.loads(
        (PIPELINE_ROOT / "data/processed/dataset_manifest.json").read_text()
    )
    run_manifest = json.loads((PIPELINE_ROOT / "models/artifacts/run_manifest.json").read_text())
    eval_report = json.loads((PIPELINE_ROOT / "evaluation/results/ct_eval_report.json").read_text())

    if not eval_report.get("passed"):
        print("ERROR: evaluation did not pass; skipping register")
        return 1

    release_id = f"{prefix}-{uuid.uuid4().hex[:8]}"
    store = ReleaseStore()
    store.create_release(
        release_id=release_id,
        name=f"CT {run_manifest.get('model_name', 'model')}",
        source_artifact=str(run_manifest.get("base_model", "unknown")),
        dataset_versions=dataset_manifest.get("splits", {}),
        training_config_ref=f"config/pipeline/params.yaml#mlflow={run_manifest.get('mlflow', {}).get('run_id')}",
        created_by="continuous-training",
    )
    store.attach_eval(
        release_id,
        eval_report_ref="training/pipeline/evaluation/results/ct_eval_report.json",
        metrics=eval_report.get("metrics"),
    )

    pointer = {
        "release_id": release_id,
        "registered_at": utc_now(),
        "mlflow_run_id": run_manifest.get("mlflow", {}).get("run_id"),
        "mlflow_model_uri": run_manifest.get("mlflow", {}).get("model_uri"),
        "mlflow_model_version": run_manifest.get("mlflow", {}).get("model_version"),
        "dataset_id": dataset_manifest.get("dataset_id"),
    }
    out = PIPELINE_ROOT / "data/pipeline/release_pointer.json"
    write_json(out, pointer)
    print(f"[+] Registered draft release {release_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
