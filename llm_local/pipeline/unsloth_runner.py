"""Invoke Unsloth fine-tune inside the training container."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from llm_local.catalog import ROOT

PIPELINE_ROOT = ROOT / "training" / "pipeline"
UNSLOTH_WORK = ROOT / "training" / "unsloth" / "work"
DEFAULT_CONTAINER = "unsloth"
DEFAULT_SCRIPT = "/workspace/scripts/finetune_lora.py"
CONTAINER_CONFIG_PATH = "/workspace/work/ct_train_config.json"


def container_running(name: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", name],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def resolve_base_model_path(base_model: str) -> str:
    """Map inventory repo id to path inside the Unsloth container."""
    if base_model.startswith("local/"):
        folder = base_model.split("/", 1)[1]
        return f"/workspace/models/{folder}"
    if base_model.startswith("/"):
        return base_model
    return base_model


def build_train_config(params: dict[str, Any], manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    train_cfg = params.get("train", {})
    model_cfg = params.get("model", {})
    unsloth_cfg = train_cfg.get("unsloth", {})
    container_output = str(unsloth_cfg.get("container_output_dir", "/workspace/pipeline/models/artifacts/staging"))
    return {
        "base_model": model_cfg.get("base_model"),
        "base_model_path": resolve_base_model_path(str(model_cfg.get("base_model", ""))),
        "dataset_id": manifest.get("dataset_id"),
        "dataset_manifest": str(PIPELINE_ROOT / "data/processed/dataset_manifest.json"),
        "output_dir": container_output,
        "host_output_dir": str(output_dir),
        "epochs": int(train_cfg.get("epochs", 1)),
        "learning_rate": float(train_cfg.get("learning_rate", 2e-4)),
        "adapter_type": str(train_cfg.get("adapter_type", "lora")),
        "max_seq_length": int(train_cfg.get("max_seq_length", 2048)),
        "batch_size": int(train_cfg.get("batch_size", 2)),
        "lora_r": int(train_cfg.get("lora_r", 16)),
        "lora_alpha": int(train_cfg.get("lora_alpha", 16)),
    }


def run_unsloth_training(
    params: dict[str, Any],
    manifest: dict[str, Any],
    *,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Run fine-tune via docker exec; returns training summary metrics."""
    train_cfg = params.get("train", {})
    unsloth_cfg = train_cfg.get("unsloth", {})
    container = str(unsloth_cfg.get("container", os.environ.get("UNSLOTH_CONTAINER", DEFAULT_CONTAINER)))
    script = str(unsloth_cfg.get("script", DEFAULT_SCRIPT))

    staging = output_dir or (PIPELINE_ROOT / "models" / "artifacts" / "staging")
    staging.mkdir(parents=True, exist_ok=True)
    try:
        staging.chmod(0o777)
    except OSError:
        pass

    if os.environ.get("UNSLOTH_TRAIN_SIMULATE", "").lower() in {"1", "true", "yes"}:
        return _simulate_training(staging, params, manifest)

    if not container_running(container):
        raise RuntimeError(
            f"Unsloth container {container!r} is not running. "
            "Start it with: ./llm-local train up"
        )

    UNSLOTH_WORK.mkdir(parents=True, exist_ok=True)
    config = build_train_config(params, manifest, staging)
    config_path = UNSLOTH_WORK / "ct_train_config.json"
    payload = json.dumps(config, indent=2) + "\n"
    try:
        config_path.write_text(payload)
    except PermissionError:
        _write_container_config(container, payload)

    exec_cmd = [
        "docker",
        "exec",
        container,
        "python",
        script,
        CONTAINER_CONFIG_PATH,
    ]
    print(f"[*] Running Unsloth fine-tune in {container}: {' '.join(exec_cmd[2:])}")
    result = subprocess.run(exec_cmd, check=False, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.returncode != 0:
        print(result.stderr, file=os.sys.stderr)
        raise RuntimeError(f"Unsloth training failed with exit code {result.returncode}")

    summary_path = staging / "training_summary.json"
    if not summary_path.is_file():
        raise RuntimeError(f"Training finished but summary not found: {summary_path}")

    summary = json.loads(summary_path.read_text())
    return {
        "final_loss": float(summary.get("final_loss", 0.0)),
        "epochs": summary.get("epochs", config["epochs"]),
        "adapter_type": config["adapter_type"],
        "artifact_dir": str(staging.relative_to(PIPELINE_ROOT)),
    }


def _simulate_training(staging: Path, params: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    train_cfg = params.get("train", {})
    model_cfg = params.get("model", {})
    adapter_type = str(train_cfg.get("adapter_type", "lora"))
    summary = {
        "final_loss": 0.21,
        "epochs": train_cfg.get("epochs", 1),
        "simulated": True,
        "base_model": model_cfg.get("base_model"),
        "dataset_id": manifest.get("dataset_id"),
    }
    staging.mkdir(parents=True, exist_ok=True)
    (staging / "adapter_config.json").write_text(
        json.dumps({"peft_type": adapter_type, "base_model": model_cfg.get("base_model")}, indent=2) + "\n"
    )
    (staging / "training_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (staging / "README.txt").write_text("Simulated adapter bundle (UNSLOTH_TRAIN_SIMULATE)\n")
    print("[*] Simulated Unsloth training (UNSLOTH_TRAIN_SIMULATE)")
    rel_artifact = (
        str(staging.relative_to(PIPELINE_ROOT))
        if staging.is_relative_to(PIPELINE_ROOT)
        else str(staging)
    )
    return {
        "final_loss": summary["final_loss"],
        "epochs": summary["epochs"],
        "adapter_type": adapter_type,
        "artifact_dir": rel_artifact,
        "simulated": True,
    }


def sync_staging_artifacts(staging: Path) -> None:
    """Ensure staging directory exists after container wrote to mounted pipeline path."""
    if not staging.is_dir():
        raise RuntimeError(f"Expected artifact staging directory missing: {staging}")


def _write_container_config(container: str, payload: str) -> None:
    result = subprocess.run(
        ["docker", "exec", "-i", "-u", "0", container, "python", "-c", (
            "from pathlib import Path; import sys; "
            f"Path('{CONTAINER_CONFIG_PATH}').write_text(sys.stdin.read())"
        )],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Failed to write training config inside container: "
            f"{result.stderr.strip() or result.stdout.strip() or result.returncode}"
        )
