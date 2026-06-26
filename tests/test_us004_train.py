"""US-004 tests: Unsloth runner simulate + train stage registry handoff."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "training" / "pipeline"


@pytest.fixture()
def pipeline_env(tmp_path, monkeypatch):
    registry = tmp_path / "registry"
    monkeypatch.setenv("RELEASE_REGISTRY_ROOT", str(registry))
    monkeypatch.setenv("CT_DRY_RUN", "true")
    monkeypatch.chdir(PIPELINE)
    return PIPELINE


def test_unsloth_simulate_writes_staging(monkeypatch, tmp_path):
    monkeypatch.setenv("UNSLOTH_TRAIN_SIMULATE", "1")
    from llm_local.pipeline.unsloth_runner import run_unsloth_training

    params = {
        "model": {"base_model": "local/sample-chat-small", "name": "mlops-ct-model"},
        "train": {"epochs": 1, "adapter_type": "lora", "learning_rate": 0.0002},
    }
    manifest = {"dataset_id": "ds-test-abc"}
    staging = tmp_path / "staging"
    result = run_unsloth_training(params, manifest, output_dir=staging)

    assert result["simulated"] is True
    assert (staging / "adapter_config.json").is_file()
    assert (staging / "training_summary.json").is_file()
    assert result["final_loss"] == 0.21


def test_train_non_dry_run_registers_mlflow(monkeypatch):
    monkeypatch.delenv("CT_DRY_RUN", raising=False)
    monkeypatch.setenv("UNSLOTH_TRAIN_SIMULATE", "1")

    manifest_path = PIPELINE / "data/processed/dataset_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "dataset_id": "ds-test-register",
                "splits": {"train": {"id": "t"}, "val": {"id": "v"}, "test": {"id": "x"}},
            }
        )
        + "\n"
    )

    fake_mlflow = {
        "run_id": "abc123",
        "model_name": "mlops-ct-model",
        "model_version": 2,
        "model_uri": "models:/mlops-ct-model/2",
        "metrics": {"loss": 0.21, "epochs": 1},
        "dry_run": False,
    }

    from llm_local.pipeline.stages import train as train_stage

    with patch.object(train_stage, "dry_run_from_env_or_params", return_value=False):
        with patch.object(train_stage, "log_training_run", return_value=fake_mlflow) as log_run:
            with patch.object(train_stage, "run_unsloth_training") as run_train:
                with patch.object(train_stage, "sync_staging_artifacts"):
                    run_train.return_value = {
                        "final_loss": 0.21,
                        "epochs": 1,
                        "adapter_type": "lora",
                        "artifact_dir": "models/artifacts/staging",
                    }
                    code = train_stage.main()

    assert code == 0
    log_run.assert_called_once()
    run_manifest = json.loads((PIPELINE / "models/artifacts/run_manifest.json").read_text())
    assert run_manifest["dry_run"] is False
    assert run_manifest["mlflow"]["model_uri"] == "models:/mlops-ct-model/2"
    assert run_manifest["mlflow"]["model_version"] == 2
