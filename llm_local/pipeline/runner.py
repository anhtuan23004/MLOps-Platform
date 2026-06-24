"""Continuous training pipeline orchestration (DVC + MLflow)."""

from __future__ import annotations

import os
import subprocess
import sys

from llm_local.catalog import ROOT
from llm_local.config_paths import PIPELINE_DIR

MLFLOW_DIR = ROOT / "training" / "mlflow"
STAGES = ("prepare_data", "train", "evaluate", "register")
STAGE_MODULES = {
    "prepare_data": "llm_local.pipeline.stages.prepare_data",
    "train": "llm_local.pipeline.stages.train",
    "evaluate": "llm_local.pipeline.stages.evaluate",
    "register": "llm_local.pipeline.stages.register",
}


def _run_stage(stage: str, *, extra_env: dict[str, str] | None = None) -> int:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    module = STAGE_MODULES[stage]
    return subprocess.run([sys.executable, "-m", module], cwd=ROOT, env=env, check=False).returncode


def run_sequential(*, dry_run: bool = False) -> int:
    env = {"CT_DRY_RUN": "true"} if dry_run else {}
    for stage in STAGES:
        print(f"=== stage: {stage} ===")
        code = _run_stage(stage, extra_env=env)
        if code != 0:
            print(f"ERROR: stage {stage} failed with exit {code}")
            return code
    print("[+] Continuous training pipeline complete")
    return 0


def dvc_available() -> bool:
    try:
        return subprocess.run(["dvc", "--version"], capture_output=True, check=False).returncode == 0
    except FileNotFoundError:
        return False


def dvc_repro(*, dry_run: bool = False) -> int:
    if not dvc_available():
        print("[!] dvc not installed; running sequential module fallback")
        return run_sequential(dry_run=dry_run)

    env = os.environ.copy()
    if dry_run:
        env["CT_DRY_RUN"] = "true"
    return subprocess.run(["dvc", "repro"], cwd=PIPELINE_DIR, env=env, check=False).returncode


def ensure_network_catalog() -> None:
    from llm_local.catalog import network_name

    subprocess.run(
        ["docker", "network", "create", network_name()],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def mlflow_up() -> int:
    from .compose import compose_with_env

    ensure_network_catalog()
    return subprocess.run(compose_with_env("mlflow", "up", "-d"), cwd=MLFLOW_DIR, check=False).returncode


def mlflow_down() -> int:
    from .compose import compose_with_env

    return subprocess.run(compose_with_env("mlflow", "down"), cwd=MLFLOW_DIR, check=False).returncode


def print_cron_install() -> int:
    repo = ROOT.resolve()
    line = (
        f"0 2 * * * cd {repo} && CT_DRY_RUN=false {repo}/llm-local train pipeline run "
        f">> {repo}/training/pipeline/logs/cron.log 2>&1"
    )
    print("Add this line to crontab (crontab -e):\n")
    print(line)
    print("\nRequires MLFLOW_TRACKING_URI, AWS_* and DVC remote configured on the host.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if not args:
        print("Usage: pipeline {run|repro|schedule} [--dry-run]")
        return 1

    command = args.pop(0)
    dry_run = "--dry-run" in args

    if command in {"run", "repro"}:
        return dvc_repro(dry_run=dry_run)
    if command == "schedule":
        if "--install-cron" in args:
            return print_cron_install()
        print("Use: train pipeline schedule --install-cron")
        return 0

    print(f"Unknown pipeline command: {command}")
    return 1
