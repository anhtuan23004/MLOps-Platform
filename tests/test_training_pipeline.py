"""Tests for continuous training pipeline scripts (dry-run)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "training" / "pipeline"


@pytest.fixture()
def pipeline_env(tmp_path, monkeypatch):
    registry = tmp_path / "registry"
    monkeypatch.setenv("RELEASE_REGISTRY_ROOT", str(registry))
    monkeypatch.setenv("CT_DRY_RUN", "true")
    monkeypatch.chdir(PIPELINE)
    return PIPELINE


def run_stage(name: str) -> subprocess.CompletedProcess[str]:
    module = f"llm_local.pipeline.stages.{name.replace('_release', '')}"
    if name == "register_release":
        module = "llm_local.pipeline.stages.register"
    return subprocess.run(
        [sys.executable, "-m", module],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_prepare_data(pipeline_env):
    result = run_stage("prepare_data")
    assert result.returncode == 0, result.stderr
    manifest = json.loads((pipeline_env / "data/processed/dataset_manifest.json").read_text())
    assert "dataset_id" in manifest
    assert "splits" in manifest
    assert manifest["schema"]["name"] == "llm-sft-jsonl"
    assert manifest["schema"]["format"] == "conversation"


def test_full_dry_run_pipeline(pipeline_env):
    for stage in ("prepare_data", "train", "evaluate", "register"):
        result = run_stage(stage)
        assert result.returncode == 0, f"{stage}: {result.stderr}"

    pointer = json.loads((pipeline_env / "data/pipeline/release_pointer.json").read_text())
    assert pointer["release_id"].startswith("rel-ct-")

    run_manifest = json.loads((pipeline_env / "models/artifacts/run_manifest.json").read_text())
    assert run_manifest["dry_run"] is True
    eval_report = json.loads((pipeline_env / "evaluation/results/ct_eval_report.json").read_text())
    assert eval_report["ground_truth_available"] is False
    assert "accuracy" not in eval_report["metrics"]


def test_public_prediction_validation_accepts_three_field_entities(tmp_path):
    from llm_local.pipeline.stages.evaluate import validate_predictions

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    (input_dir / "1.txt").write_text("Bệnh nhân không sốt và đang dùng metformin.")
    (output_dir / "1.json").write_text(
        json.dumps(
            [
                {"text": "sốt", "type": "TRIỆU_CHỨNG", "assertions": ["isNegated"]},
                {"text": "metformin", "type": "THUỐC", "assertions": []},
            ],
            ensure_ascii=False,
        )
    )

    metrics, errors = validate_predictions(input_dir, output_dir)

    assert errors == []
    assert metrics["file_coverage"] == 1.0
    assert metrics["schema_valid_file_rate"] == 1.0
    assert metrics["valid_entity_rate"] == 1.0


def test_public_prediction_validation_rejects_extra_model_fields(tmp_path):
    from llm_local.pipeline.stages.evaluate import validate_predictions

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    (input_dir / "1.txt").write_text("Bệnh nhân sốt.")
    (output_dir / "1.json").write_text(
        json.dumps(
            [
                {
                    "text": "sốt",
                    "type": "TRIỆU_CHỨNG",
                    "assertions": [],
                    "position": [10, 13],
                }
            ],
            ensure_ascii=False,
        )
    )

    metrics, errors = validate_predictions(input_dir, output_dir)

    assert metrics["schema_valid_file_rate"] == 0.0
    assert "requires exactly text, type, assertions" in errors[0]


def test_evaluation_paths_must_be_repo_relative():
    from llm_local.pipeline.stages.evaluate import repo_path

    with pytest.raises(ValueError, match="repo-relative"):
        repo_path("/tmp/non-portable-input")

    assert repo_path("data/input") == ROOT / "data/input"


def test_simulated_inference_runs_without_docker(tmp_path):
    from llm_local.pipeline.unsloth_runner import run_unsloth_inference

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    (input_dir / "1.txt").write_text("Bệnh nhân sốt.")

    count = run_unsloth_inference({}, input_dir=input_dir, output_dir=output_dir, simulate=True)

    assert count == 1
    assert (output_dir / "1.json").read_text() == "[]\n"


def test_llm_local_pipeline_run_dry(tmp_path):
    env = {**os.environ, "CT_DRY_RUN": "true", "RELEASE_REGISTRY_ROOT": str(tmp_path / "registry")}
    result = subprocess.run(
        [str(ROOT / "llm-local"), "train", "pipeline", "run", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_pipeline_uses_local_registry_when_default_not_writable(monkeypatch, tmp_path):
    from llm_local.pipeline import runner

    monkeypatch.delenv("RELEASE_REGISTRY_ROOT", raising=False)
    fallback = tmp_path / "release-registry"
    monkeypatch.setattr(runner, "LOCAL_REGISTRY_ROOT", fallback)
    monkeypatch.setattr(runner, "default_registry_root", lambda: ROOT / "data" / "release-registry")
    monkeypatch.setattr(runner, "_can_write_registry_root", lambda path: False)

    env = runner._pipeline_env(dry_run=False)

    assert env["CT_DRY_RUN"] == "false"
    assert env["RELEASE_REGISTRY_ROOT"] == str(fallback)
    assert fallback.is_dir()


def test_pipeline_bootstraps_dvc_config_from_template(monkeypatch, tmp_path):
    from llm_local.pipeline import runner

    pipeline_dir = tmp_path / "pipeline"
    dvc_dir = pipeline_dir / ".dvc"
    dvc_dir.mkdir(parents=True)
    template = tmp_path / "config.example"
    template.write_text("[core]\n    remote = s3remote\n")

    monkeypatch.setattr(runner, "PIPELINE_DIR", pipeline_dir)
    monkeypatch.setattr(runner, "DVC_CONFIG_EXAMPLE", template)

    runner.ensure_dvc_repo_layout()

    assert (dvc_dir / "config").read_text() == template.read_text()


def test_dvc_pipeline_uses_portable_stage_wrapper():
    data = YAML(typ="safe").load((PIPELINE / "dvc.yaml").read_text())
    stages = data["stages"]

    assert stages["prepare_data"]["cmd"] == "./run_stage.sh prepare_data"
    assert stages["train"]["cmd"] == "./run_stage.sh train"
    assert stages["evaluate"]["cmd"] == "./run_stage.sh evaluate"
    assert stages["register"]["cmd"] == "./run_stage.sh register"
