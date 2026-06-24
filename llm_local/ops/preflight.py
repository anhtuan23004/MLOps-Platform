#!/usr/bin/env python3
"""Preflight checks for local runtime startup."""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_local.catalog import format_targets, preflight_services
from llm_local.models.registry import model_targets


SERVICES = preflight_services()
FORMAT_TARGETS = format_targets()


def run(*cmd: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(cmd, 127, "", str(exc))


def load_env(service: str) -> dict[str, str]:
    spec = SERVICES[service]
    env: dict[str, str] = {}
    for name in (".env.example", ".env"):
        path = ROOT / spec["dir"] / name
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = os.path.expandvars(value.strip().strip('"').strip("'"))
    return env


def container_state(name: str) -> str:
    result = run("docker", "inspect", "--format={{.State.Status}}", name)
    if result.returncode != 0:
        return "missing"
    return result.stdout.strip() or "unknown"


def container_health(name: str) -> str:
    result = run("docker", "inspect", "--format={{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}", name)
    if result.returncode != 0:
        return "missing"
    return result.stdout.strip() or "unknown"


def gpu_count() -> int | None:
    result = run("nvidia-smi", "-L")
    if result.returncode != 0:
        return None
    return len([line for line in result.stdout.splitlines() if line.startswith("GPU ")])


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def registry_models() -> list[dict[str, object]]:
    try:
        from ruamel.yaml import YAML
    except ImportError:
        return []
    path = ROOT / "models" / "registry.yaml"
    if not path.exists():
        return []
    with path.open() as handle:
        data = YAML().load(handle) or {}
    return data.get("models", []) or []


def targets_for(model: dict[str, object]) -> list[str]:
    return [str(target) for target in model_targets(model)]


def find_model_by_container_path(path: str) -> dict[str, object] | None:
    if not path.startswith("/models/"):
        return None
    selected = path.removeprefix("/models/").split("/", 1)[0]
    for model in registry_models():
        model_path = str(model.get("path", ""))
        if Path(model_path).name == selected:
            return model
    return None


def host_model_path(service: str, container_path: str) -> Path | None:
    if not container_path.startswith("/models/"):
        return None
    env = load_env(service)
    local_root = env.get("MODEL_LOCAL_PATH", "../../models")
    root_path = (ROOT / SERVICES[service]["dir"] / local_root).resolve()
    return root_path / container_path.removeprefix("/models/")


def validate_mounted_model_path(
    service: str,
    key: str,
    container_path: str,
    failures: list[str],
    warnings: list[str],
    *,
    required: bool,
) -> bool:
    if not container_path:
        if required:
            warnings.append(f"{service}: no {key} configured")
        return False
    if not container_path.startswith("/models/"):
        failures.append(f"{service}: {key} must use the mounted /models/... path, got: {container_path}")
        return False
    host_path = host_model_path(service, container_path)
    if host_path is not None and not host_path.exists():
        failures.append(f"{service}: configured {key} does not exist on host: {host_path}")
        return False
    return True


def check_model_compatibility(service: str, failures: list[str], warnings: list[str]) -> None:
    model_key = SERVICES[service].get("model_key")
    if not model_key:
        return
    env = load_env(service)
    model_path = env.get(str(model_key), "")
    if not validate_mounted_model_path(service, str(model_key), model_path, failures, warnings, required=True):
        return
    model = find_model_by_container_path(model_path)
    if not model:
        warnings.append(f"{service}: {model_path} is not registered in local models/registry.yaml")
        return
    model_id = str(model.get("id", "?"))
    fmt = str(model.get("format", ""))
    allowed = FORMAT_TARGETS.get(fmt, set())
    targets = set(targets_for(model))
    if service not in targets:
        failures.append(f"{service}: model {model_id} is not targeted for this runtime")
    if service not in allowed:
        failures.append(f"{service}: model {model_id} format {fmt!r} is not compatible with this runtime")


def check_ports(service: str, failures: list[str], warnings: list[str]) -> None:
    port_spec = SERVICES[service].get("host_port")
    if not port_spec:
        return
    key, default = port_spec
    env = load_env(service)
    port = int(env.get(key, default))
    container = SERVICES[service].get("container")
    if port_open(port) and not container:
        failures.append(f"{service}: host port {port} is already in use")
    elif port_open(port) and container_state(str(container)) != "running":
        failures.append(f"{service}: host port {port} is already in use before {container} is running")
    elif port_open(port):
        warnings.append(f"{service}: host port {port} is already open by running container {container}")


def check_gpu_policy(target: str | None, failures: list[str], warnings: list[str]) -> None:
    gpu_services = {name: spec for name, spec in SERVICES.items() if spec.get("gpu")}
    target_gpu = bool(target and SERVICES[target].get("gpu"))
    count = gpu_count()

    if target_gpu and count is None and os.environ.get("LLM_LOCAL_SKIP_GPU_CHECK") != "1":
        failures.append(
            f"{target}: nvidia-smi is unavailable; set LLM_LOCAL_SKIP_GPU_CHECK=1 only if Docker GPU access is known-good"
        )
    elif count == 0 and target_gpu:
        failures.append(f"{target}: no NVIDIA GPU detected")

    running = [
        name
        for name, spec in gpu_services.items()
        if spec.get("container") and container_state(str(spec["container"])) == "running"
    ]
    running_without_target = [name for name in running if name != target]
    all_gpu_running = [name for name in running_without_target if gpu_services[name].get("all_gpus")]

    if target_gpu and all_gpu_running:
        failures.append(
            f"{target}: {', '.join(all_gpu_running)} already claims all GPUs; stop it first per decision 0005"
        )
    if target and SERVICES[target].get("all_gpus") and running_without_target:
        failures.append(
            f"{target}: it claims all GPUs and cannot start while {', '.join(running_without_target)} is running"
        )
    if count == 1 and target_gpu and running_without_target:
        failures.append(
            f"{target}: single-GPU host already has GPU runtime(s) running: {', '.join(running_without_target)}"
        )
    if count and count > 1 and len(running) > count:
        warnings.append(f"running GPU service count ({len(running)}) exceeds detected GPU count ({count})")


def check_health(warnings: list[str]) -> None:
    for service, spec in SERVICES.items():
        if not spec.get("container"):
            continue
        container = str(spec["container"])
        state = container_state(container)
        if state == "missing":
            continue
        health = container_health(container)
        if health not in {"running", "healthy"}:
            warnings.append(f"{service}: container {container} health/state is {health}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MLOps-Platform startup guardrails")
    parser.add_argument("service", nargs="?", choices=sorted(SERVICES), help="service being started")
    parser.add_argument("--all", action="store_true", help="check all known service ports and model configs")
    args = parser.parse_args()

    services = sorted(SERVICES) if args.all else ([args.service] if args.service else [])
    failures: list[str] = []
    warnings: list[str] = []

    for service in services:
        check_ports(service, failures, warnings)
        check_model_compatibility(service, failures, warnings)
    check_gpu_policy(args.service, failures, warnings)
    check_health(warnings)

    print("=== Guardrails ===")
    for warning in warnings:
        print(f"  WARN: {warning}")
    for failure in failures:
        print(f"  FAIL: {failure}")
    if failures:
        return 1
    print("  OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
