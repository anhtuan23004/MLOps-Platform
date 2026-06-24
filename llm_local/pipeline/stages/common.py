"""Shared helpers for continuous training pipeline stages."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from llm_local.config_paths import PIPELINE_PARAMS_FILE, PIPELINE_DIR

PIPELINE_ROOT = PIPELINE_DIR
_yaml = YAML(typ="safe")


def load_params() -> dict[str, Any]:
    with PIPELINE_PARAMS_FILE.open() as handle:
        return _yaml.load(handle) or {}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_directory(directory: Path) -> str:
    if not directory.exists():
        return "empty"
    files = sorted(p for p in directory.rglob("*") if p.is_file())
    if not files:
        return "empty"
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(directory)).encode())
        digest.update(sha256_file(path).encode())
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def mlflow_tracking_uri() -> str:
    return os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:15000")


def dry_run_from_env_or_params(params: dict[str, Any]) -> bool:
    if os.environ.get("CT_DRY_RUN", "").lower() in {"1", "true", "yes"}:
        return True
    return bool(params.get("train", {}).get("dry_run", True))
