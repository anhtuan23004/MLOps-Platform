"""MLflow GenAI tracing setup for the LiteLLM gateway (US-005)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from llm_local.catalog import ROOT
from llm_local.config_paths import LITELLM_CONFIG_FILE, LITELLM_TRACING_CONFIG_FILE, load_mlflow_genai, ACTIVE_LITELLM_CONFIG

_yaml = YAML(typ="safe")


def tracing_enabled(cfg: dict[str, Any] | None = None) -> bool:
    data = cfg if cfg is not None else load_mlflow_genai()
    return bool((data.get("genai") or {}).get("tracing_enabled", False))


def tracing_experiment(cfg: dict[str, Any] | None = None) -> str:
    data = cfg if cfg is not None else load_mlflow_genai()
    experiments = (data.get("mlflow") or {}).get("experiments") or {}
    return str(experiments.get("serving_traces", "mlops-platform-serving-traces"))


def tracking_uri_docker(cfg: dict[str, Any] | None = None) -> str:
    data = cfg if cfg is not None else load_mlflow_genai()
    return str((data.get("mlflow") or {}).get("tracking_uri_docker", "http://mlflow:5000"))


def source_litellm_config(cfg: dict[str, Any] | None = None) -> Path:
    if tracing_enabled(cfg):
        return LITELLM_TRACING_CONFIG_FILE
    return LITELLM_CONFIG_FILE


def litellm_tracing_env(cfg: dict[str, Any] | None = None) -> dict[str, str]:
    if not tracing_enabled(cfg):
        return {}
    data = cfg if cfg is not None else load_mlflow_genai()
    return {
        "MLFLOW_TRACKING_URI": tracking_uri_docker(data),
        "MLFLOW_EXPERIMENT_NAME": tracing_experiment(data),
    }


def prepare_litellm_runtime_config(cfg: dict[str, Any] | None = None) -> Path:
    """Write config/active/litellm-config.yaml for the LiteLLM compose mount."""
    data = cfg if cfg is not None else load_mlflow_genai()
    source = source_litellm_config(data)
    if not source.is_file():
        raise FileNotFoundError(f"LiteLLM config not found: {source}")

    ACTIVE_LITELLM_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, ACTIVE_LITELLM_CONFIG)
    return ACTIVE_LITELLM_CONFIG


def merge_tracing_into_env_file(env_file: Path, cfg: dict[str, Any] | None = None) -> None:
    """Add or remove MLflow tracing keys in config/env/litellm.env."""
    from llm_local.config_paths import ensure_local_env

    path = env_file if env_file.is_file() else ensure_local_env("litellm")
    lines = path.read_text().splitlines(keepends=True) if path.is_file() else []
    tracing_keys = {"MLFLOW_TRACKING_URI", "MLFLOW_EXPERIMENT_NAME"}
    merged = [line for line in lines if line.split("=", 1)[0].strip() not in tracing_keys]

    for key, value in litellm_tracing_env(cfg).items():
        merged.append(f"{key}={value}\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(merged))


def prepare_litellm_serving(cfg: dict[str, Any] | None = None) -> bool:
    """Render LiteLLM runtime config + env. Returns whether tracing is enabled."""
    data = cfg if cfg is not None else load_mlflow_genai()
    prepare_litellm_runtime_config(data)
    merge_tracing_into_env_file(ROOT / "config" / "env" / "litellm.env", data)
    return tracing_enabled(data)
