"""Central configuration paths for MLOps-Platform."""

from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from llm_local.catalog import ROOT, service

CONFIG_DIR = ROOT / "config"
PLATFORM_PATH = CONFIG_DIR / "platform.yaml"
_yaml = YAML(typ="safe")


@lru_cache(maxsize=1)
def load_platform() -> dict[str, Any]:
    with PLATFORM_PATH.open() as handle:
        return _yaml.load(handle) or {}


def config_path(key: str) -> Path:
    rel = (load_platform().get("paths") or {}).get(key)
    if not rel:
        raise KeyError(f"unknown platform path key: {key}")
    return ROOT / str(rel)


def env_profile(service_id: str) -> str:
    return str(service(service_id).get("env_profile", service_id))


def env_paths(profile: str) -> tuple[Path, Path]:
    env_cfg = (load_platform().get("env") or {}).get(profile) or {}
    example = ROOT / str(env_cfg.get("example", f"config/env/{profile}.env.example"))
    local = ROOT / str(env_cfg.get("local", f"config/env/{profile}.env"))
    return example, local


def service_env_paths(service_id: str) -> tuple[Path, Path]:
    return env_paths(env_profile(service_id))


def ensure_local_env(service_id: str) -> Path:
    example, local = service_env_paths(service_id)
    if not local.is_file():
        if not example.is_file():
            raise FileNotFoundError(f"missing env template: {example}")
        local.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(example, local)
    return local


def init_local_env_files() -> list[Path]:
    created: list[Path] = []
    for profile in sorted((load_platform().get("env") or {})):
        example, local = env_paths(profile)
        if local.is_file() or not example.is_file():
            continue
        local.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(example, local)
        created.append(local)
    return created


# Committed config files
DESIRED_MODELS_FILE = config_path("desired_models")
PRESETS_FILE = config_path("presets")
PIPELINE_PARAMS_FILE = config_path("pipeline_params")
DVC_CONFIG_EXAMPLE = config_path("dvc_config_example")
LITELLM_CONFIG_FILE = config_path("litellm_config")
LITELLM_TRACING_CONFIG_FILE = config_path("litellm_config_tracing")
MLFLOW_GENAI_FILE = config_path("mlflow_genai")
ACTIVE_SERVING_STATE = config_path("active_serving_state")
ACTIVE_LITELLM_CONFIG = config_path("active_litellm_config")


@lru_cache(maxsize=1)
def load_mlflow_genai() -> dict[str, Any]:
    with MLFLOW_GENAI_FILE.open() as handle:
        return _yaml.load(handle) or {}


# Model weights stay under models/
MODELS_DATA_DIR = ROOT / "models"
REGISTRY_FILE = MODELS_DATA_DIR / "registry.yaml"
PIPELINE_DIR = ROOT / "training" / "pipeline"
