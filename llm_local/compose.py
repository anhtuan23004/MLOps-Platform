"""Docker Compose command resolution."""

from __future__ import annotations

import os
import shlex
import subprocess
from functools import lru_cache


@lru_cache(maxsize=1)
def compose_command() -> list[str]:
    override = os.environ.get("LLM_LOCAL_COMPOSE_COMMAND")
    if override:
        return shlex.split(override)

    candidates = (["docker", "compose"], ["docker-compose"])
    for candidate in candidates:
        if _command_works([*candidate, "version"]) and _command_works([*candidate, "up", "--help"]):
            return candidate

    raise RuntimeError(
        "Docker Compose is unavailable. Install the Docker Compose v2 plugin, "
        "install docker-compose, or set LLM_LOCAL_COMPOSE_COMMAND."
    )


def compose_args(*args: str) -> list[str]:
    return [*compose_command(), *args]


def _command_works(command: list[str]) -> bool:
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0
