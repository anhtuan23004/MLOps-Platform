"""Apply release promotion and rollback to live vLLM serving."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from llm_local.catalog import ROOT, host_port, service


def apply_model_to_runtime(model_id: str, *, restart: bool = True) -> None:
    """Select model for vLLM and optionally restart the runtime."""
    command = [sys.executable, "-m", "llm_local.models.manage", "select", model_id, "--runtime", "vllm"]
    if restart:
        command.append("--restart")
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"failed to select model {model_id} for vllm (exit {result.returncode})")


def wait_for_vllm_health(*, timeout_s: int = 300, poll_s: float = 5.0) -> None:
    """Wait until vLLM health endpoint responds or timeout."""
    spec = service("vllm")
    check = spec.get("runtime_check") or {}
    endpoint_template = check.get("host_endpoint")
    port = host_port("vllm")
    if not endpoint_template or port is None:
        raise RuntimeError("vLLM runtime_check host_endpoint not configured in catalog")

    url = str(endpoint_template).format(host_port=port)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["curl", "-sf", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(poll_s)
    raise RuntimeError(f"vLLM health check timed out after {timeout_s}s: {url}")


def run_preflight(service_id: str = "vllm") -> None:
    result = subprocess.run(
        [sys.executable, "-m", "llm_local.ops.preflight", service_id],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"preflight failed for {service_id} (exit {result.returncode})")


def apply_release_serving(
    record: dict[str, object],
    *,
    restart: bool = True,
    wait_health: bool = True,
) -> None:
    """Switch vLLM to the release's source_artifact model."""
    model_id = str(record.get("source_artifact", "")).strip()
    if not model_id:
        raise RuntimeError("release record missing source_artifact")
    apply_model_to_runtime(model_id, restart=restart)
    if wait_health and restart:
        wait_for_vllm_health()
        run_preflight("vllm")


def docker_available() -> bool:
    return subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def serving_env_ready() -> bool:
    """Best-effort check that vLLM compose dir exists."""
    return (ROOT / "serving" / "vllm" / "docker-compose.yml").is_file()
