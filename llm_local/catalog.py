"""Runtime catalog access for MLOps-Platform."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "config" / "runtime-catalog.yaml"
FLOATING_TAGS = {"latest", "main", "main-stable", "stable", "dev"}


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    with CATALOG_PATH.open() as handle:
        return YAML().load(handle) or {}


def network_name() -> str:
    return str(load_catalog().get("network", "llm-net"))


def services() -> dict[str, dict[str, Any]]:
    return load_catalog().get("services", {}) or {}


def service(service_id: str) -> dict[str, Any]:
    try:
        return services()[service_id]
    except KeyError as exc:
        raise KeyError(f"unknown service: {service_id}") from exc


def service_ids() -> list[str]:
    return sorted(services())


def services_by_group(group: str) -> list[str]:
    return [service_id for service_id, spec in services().items() if spec.get("group") == group]


def compose_files() -> list[Path]:
    seen: set[str] = set()
    files: list[Path] = []
    for spec in services().values():
        compose_file = spec.get("compose_file")
        if not compose_file or compose_file in seen:
            continue
        seen.add(str(compose_file))
        files.append(ROOT / str(compose_file))
    return files


def service_dir(service_id: str) -> Path:
    return ROOT / str(service(service_id)["dir"])


def host_port(service_id: str) -> int | None:
    spec = service(service_id)
    port = spec.get("host_port")
    if not port:
        return None
    env = load_service_env(service_id)
    return int(env.get(str(port["env"]), port["default"]))


def load_service_env(service_id: str) -> dict[str, str]:
    env: dict[str, str] = {}
    directory = service_dir(service_id)
    for name in (".env.example", ".env"):
        path = directory / name
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = os.path.expandvars(value.strip().strip('"').strip("'"))
    return env


def preflight_services() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for service_id, spec in services().items():
        gpu = spec.get("gpu") or {}
        host = spec.get("host_port")
        model = spec.get("model") or {}
        item: dict[str, Any] = {
            "dir": spec.get("dir"),
            "container": spec.get("container"),
            "host_port": (host["env"], host["default"]) if host else None,
            "gpu": bool(gpu.get("enabled")),
            "all_gpus": bool(gpu.get("all_gpus")),
        }
        if model.get("path_env"):
            item["model_key"] = model["path_env"]
        result[service_id] = item
    return result


def format_targets() -> dict[str, set[str]]:
    formats = load_catalog().get("formats", {}) or {}
    return {
        fmt: set(data.get("compatible_runtimes", []) or [])
        for fmt, data in formats.items()
    }


def runtime_env_map() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for service_id, spec in services().items():
        model = spec.get("model") or {}
        select_env = model.get("select_env")
        if select_env:
            result[service_id] = {"dir": spec["dir"], "keys": dict(select_env)}
    return result


def litellm_model_keys() -> dict[str, str]:
    result: dict[str, str] = {}
    for service_id, spec in services().items():
        model = spec.get("model") or {}
        if model.get("litellm_model_env"):
            result[service_id] = str(model["litellm_model_env"])
    return result


def gateway_alias(service_id: str) -> str | None:
    value = service(service_id).get("gateway_alias")
    return str(value) if value else None


def eval_targets() -> dict[str, str]:
    result: dict[str, str] = {}
    for service_id, spec in services().items():
        if spec.get("eval_endpoint"):
            result[service_id] = str(spec["eval_endpoint"])
    return result


def status_services() -> list[str]:
    return [service_id for service_id, spec in services().items() if spec.get("status")]


def image_specs() -> list[tuple[str, dict[str, Any]]]:
    images: list[tuple[str, dict[str, Any]]] = []
    for service_id, spec in services().items():
        image = spec.get("image")
        if image:
            images.append((service_id, image))
    return images


def is_floating_tag(tag: str) -> bool:
    lowered = tag.lower()
    return lowered in FLOATING_TAGS or lowered.startswith("nightly")


def runtime_check_services() -> list[str]:
    return [
        service_id
        for service_id, spec in services().items()
        if spec.get("runtime_check")
    ]


def validation_commands() -> dict[str, dict[str, Any]]:
    path = ROOT / "config" / "validation-commands.yaml"
    if not path.exists():
        return {}
    with path.open() as handle:
        data = YAML().load(handle) or {}
    return data.get("commands", {}) or {}
