"""Continuous training pipeline orchestration (DVC + MLflow)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from llm_local.catalog import ROOT
from llm_local.compose import compose_with_env
from llm_local.config_paths import DVC_CONFIG_EXAMPLE, PIPELINE_DIR
from llm_local.releases.store import default_registry_root

MLFLOW_DIR = ROOT / "training" / "mlflow"
PIPELINE_STATE_DIR = PIPELINE_DIR / ".state"
LOCAL_REGISTRY_ROOT = PIPELINE_STATE_DIR / "release-registry"
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


def _can_write_registry_root(path: Path) -> bool:
    candidates = [path, path / "releases", path / "aliases", path / "audit"]
    for candidate in candidates:
        probe = candidate
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        if not os.access(probe, os.W_OK):
            return False
    return True


def _pipeline_env(*, dry_run: bool) -> dict[str, str]:
    env: dict[str, str] = {"CT_DRY_RUN": "true" if dry_run else "false"}
    if "RELEASE_REGISTRY_ROOT" not in os.environ:
        default_root = default_registry_root()
        if not _can_write_registry_root(default_root):
            LOCAL_REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)
            env["RELEASE_REGISTRY_ROOT"] = str(LOCAL_REGISTRY_ROOT)
            print(
                "[!] default release registry is not writable; "
                f"using pipeline-local registry {LOCAL_REGISTRY_ROOT}"
            )
    return env


def run_sequential(*, dry_run: bool = False) -> int:
    env = _pipeline_env(dry_run=dry_run)
    for stage in STAGES:
        print(f"=== stage: {stage} ===")
        code = _run_stage(stage, extra_env=env)
        if code != 0:
            print(f"ERROR: stage {stage} failed with exit {code}")
            return code
    print("[+] Continuous training pipeline complete")
    return 0


def dvc_available() -> bool:
    dvc_cmd = dvc_command()
    try:
        return subprocess.run(dvc_cmd + ["--version"], capture_output=True, check=False).returncode == 0
    except FileNotFoundError:
        return False


def dvc_repo_available() -> bool:
    return (PIPELINE_DIR / ".dvc").exists()


def ensure_dvc_repo_layout() -> None:
    dvc_dir = PIPELINE_DIR / ".dvc"
    dvc_dir.mkdir(parents=True, exist_ok=True)
    config_path = dvc_dir / "config"
    if not config_path.exists() and DVC_CONFIG_EXAMPLE.exists():
        shutil.copy2(DVC_CONFIG_EXAMPLE, config_path)
        try:
            display_path = config_path.relative_to(ROOT)
        except ValueError:
            display_path = config_path
        print(f"[*] Initialized DVC config from template: {display_path}")


def dvc_command() -> list[str]:
    candidates = [
        ROOT / ".venv" / "bin" / "dvc",
        Path(sys.executable).resolve().parent / "dvc",
    ]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return [str(candidate)]
    return ["dvc"]


def dvc_repro(*, dry_run: bool = False) -> int:
    if not dvc_available():
        print("[!] dvc not installed; running sequential module fallback")
        return run_sequential(dry_run=dry_run)
    ensure_dvc_repo_layout()
    if not dvc_repo_available():
        print("[!] training/pipeline is not initialized as a DVC repo; running sequential module fallback")
        return run_sequential(dry_run=dry_run)

    env = os.environ.copy()
    env.update(_pipeline_env(dry_run=dry_run))
    return subprocess.run(dvc_command() + ["repro"], cwd=PIPELINE_DIR, env=env, check=False).returncode


def ensure_network_catalog() -> None:
    from llm_local.catalog import network_name

    subprocess.run(
        ["docker", "network", "create", network_name()],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def mlflow_up() -> int:
    ensure_network_catalog()
    return subprocess.run(compose_with_env("mlflow", "up", "-d"), cwd=MLFLOW_DIR, check=False).returncode


def mlflow_down() -> int:
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
