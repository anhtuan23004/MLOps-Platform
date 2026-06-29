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


def test_full_dry_run_pipeline(pipeline_env):
    for stage in ("prepare_data", "train", "evaluate", "register"):
        result = run_stage(stage)
        assert result.returncode == 0, f"{stage}: {result.stderr}"

    pointer = json.loads((pipeline_env / "data/pipeline/release_pointer.json").read_text())
    assert pointer["release_id"].startswith("rel-ct-")

    run_manifest = json.loads((pipeline_env / "models/artifacts/run_manifest.json").read_text())
    assert run_manifest["dry_run"] is True


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
