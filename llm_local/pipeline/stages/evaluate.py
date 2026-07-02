"""Run public-test inference and validate structured predictions."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from llm_local.catalog import ROOT
from llm_local.pipeline.unsloth_runner import run_unsloth_inference
from llm_local.pipeline.stages.common import PIPELINE_ROOT, load_params, utc_now, write_json

ALLOWED_TYPES = {
    "TRIỆU_CHỨNG",
    "TÊN_XÉT_NGHIỆM",
    "KẾT_QUẢ_XÉT_NGHIỆM",
    "CHẨN_ĐOÁN",
    "THUỐC",
}
ALLOWED_ASSERTIONS = {"isNegated", "isFamily", "isHistorical"}
ENTITY_FIELDS = {"text", "type", "assertions"}


def repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"evaluation path must be repo-relative: {value}")
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(f"evaluation path escapes repository: {value}")
    return resolved


def validate_predictions(input_dir: Path, output_dir: Path) -> tuple[dict[str, Any], list[str]]:
    sources = {path.stem: path for path in input_dir.glob("*.txt")}
    predictions = {path.stem: path for path in output_dir.glob("*.json")}
    errors = [f"missing prediction: {name}.json" for name in sorted(sources.keys() - predictions)]
    errors.extend(f"unexpected prediction: {name}.json" for name in sorted(predictions.keys() - sources))

    valid_files = 0
    entity_count = 0
    valid_entities = 0
    for name in sorted(sources.keys() & predictions):
        source = sources[name].read_text()
        path = predictions[name]
        file_valid = True
        try:
            entities = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(entities, list):
            errors.append(f"{path.name}: top-level value must be an array")
            continue

        for index, entity in enumerate(entities):
            entity_count += 1
            location = f"{path.name}[{index}]"
            entity_errors: list[str] = []
            if not isinstance(entity, dict) or set(entity) != ENTITY_FIELDS:
                entity_errors.append("requires exactly text, type, assertions")
            else:
                text = entity["text"]
                entity_type = entity["type"]
                assertions = entity["assertions"]
                if not isinstance(text, str) or not text or text not in source:
                    entity_errors.append("text must be a non-empty exact source span")
                if not isinstance(entity_type, str) or entity_type not in ALLOWED_TYPES:
                    entity_errors.append("invalid type")
                if (
                    not isinstance(assertions, list)
                    or not all(isinstance(value, str) for value in assertions)
                    or len(assertions) != len(set(assertions))
                    or not set(assertions) <= ALLOWED_ASSERTIONS
                ):
                    entity_errors.append("invalid assertions")
            if entity_errors:
                file_valid = False
                errors.append(f"{location}: {', '.join(entity_errors)}")
            else:
                valid_entities += 1
        if file_valid:
            valid_files += 1

    source_count = len(sources)
    prediction_count = len(predictions)
    metrics = {
        "input_records": source_count,
        "prediction_files": prediction_count,
        "predicted_entities": entity_count,
        "file_coverage": prediction_count / source_count if source_count else 0.0,
        "schema_valid_file_rate": valid_files / source_count if source_count else 0.0,
        "valid_entity_rate": valid_entities / entity_count if entity_count else 1.0,
    }
    return metrics, errors


def main() -> int:
    params = load_params()
    eval_cfg = params.get("evaluate", {})
    run_manifest = json.loads((PIPELINE_ROOT / "models/artifacts/run_manifest.json").read_text())
    dry_run = bool(run_manifest.get("dry_run", True))
    inference_simulated = dry_run or os.environ.get("UNSLOTH_TRAIN_SIMULATE", "").lower() in {
        "1",
        "true",
        "yes",
    }
    input_dir = repo_path(str(eval_cfg.get("input_dir", "data/input")))
    output_dir = repo_path(
        str(eval_cfg.get("output_dir", "training/pipeline/evaluation/predictions"))
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.is_dir():
        metrics = {
            "input_records": 0,
            "prediction_files": 0,
            "predicted_entities": 0,
            "file_coverage": 0.0,
            "schema_valid_file_rate": 0.0,
            "valid_entity_rate": 0.0,
        }
        errors = [f"input directory not found: {input_dir}"]
        skipped = dry_run
    else:
        run_unsloth_inference(
            params,
            input_dir=input_dir,
            output_dir=output_dir,
            simulate=inference_simulated,
        )
        metrics, errors = validate_predictions(input_dir, output_dir)
        skipped = False
    passed = (not errors and metrics["input_records"] > 0) or skipped

    report = {
        "evaluated_at": utc_now(),
        "dataset_id": run_manifest.get("dataset_id"),
        "mlflow_run_id": run_manifest.get("mlflow", {}).get("run_id"),
        "input_dir": str(input_dir),
        "prediction_dir": str(output_dir),
        "ground_truth_available": False,
        "metrics": metrics,
        "errors": errors,
        "passed": passed,
        "dry_run": dry_run,
        "inference_simulated": inference_simulated,
        "skipped": skipped,
    }

    out = PIPELINE_ROOT / "evaluation/results/ct_eval_report.json"
    write_json(out, report)
    print(
        f"[+] Public inference validation passed={passed} "
        f"files={metrics['prediction_files']}/{metrics['input_records']}"
    )
    return 1 if not passed else 0


if __name__ == "__main__":
    raise SystemExit(main())
