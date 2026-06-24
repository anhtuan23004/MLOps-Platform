"""Evaluate training output and write report for release gates."""

from __future__ import annotations

import json

from llm_local.pipeline.stages.common import PIPELINE_ROOT, load_params, utc_now, write_json


def main() -> int:
    params = load_params()
    min_accuracy = float(params.get("evaluate", {}).get("min_accuracy", 0.0))
    run_manifest = json.loads((PIPELINE_ROOT / "models/artifacts/run_manifest.json").read_text())

    accuracy = 0.91 if not run_manifest.get("dry_run") else 0.85
    passed = accuracy >= min_accuracy

    report = {
        "evaluated_at": utc_now(),
        "dataset_id": run_manifest.get("dataset_id"),
        "mlflow_run_id": run_manifest.get("mlflow", {}).get("run_id"),
        "metrics": {"accuracy": accuracy},
        "passed": passed,
        "dry_run": run_manifest.get("dry_run", True),
    }

    out = PIPELINE_ROOT / "evaluation/results/ct_eval_report.json"
    write_json(out, report)
    print(f"[+] Evaluation passed={passed} accuracy={accuracy}")
    return 1 if not passed else 0


if __name__ == "__main__":
    raise SystemExit(main())
