"""Tests for continuous training pipeline scripts (dry-run)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

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
