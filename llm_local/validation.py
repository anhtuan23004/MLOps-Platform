"""Executable validation ladder for MLOps-Platform."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from ruamel.yaml import YAML

from .catalog import (
    ROOT,
    compose_files,
    host_port,
    image_specs,
    network_name,
    runtime_check_services,
    service_ids,
    service,
    service_dir,
    validation_commands,
)
from .compose import compose_args


REGISTRY_COMPOSE = ROOT / "tests" / "integration" / "release_registry" / "docker-compose.yml"


class ValidationRunner:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, label: str, command: Sequence[str], cwd: Path | None = None) -> None:
        result = subprocess.run(command, cwd=cwd or ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            print(f"  PASS {label}")
            self.passed += 1
        else:
            print(f"  FAIL {label}")
            self.failed += 1

    def check_python(self, label: str, code: str) -> None:
        self.check(label, [sys.executable, "-c", code])

    def section(self, title: str) -> None:
        print(f"=== {title} ===")

    def finish(self) -> int:
        print("")
        print(f"Results: {self.passed} passed, {self.failed} failed")
        return 1 if self.failed else 0


def run_quick(include_runtime: bool = False) -> int:
    runner = ValidationRunner()
    check_catalog(runner)
    check_compose(runner)
    check_models(runner, metadata_only=True)
    check_scripts(runner)
    check_dashboards(runner)
    check_makefile(runner)
    check_images(runner)
    if include_runtime:
        check_runtime(runner)
    else:
        runner.section("Runtime Checks")
        print("  skipped (run ./llm-local validate quick --runtime to check live services)")
    return runner.finish()


def run_integration() -> int:
    runner = ValidationRunner()
    check_catalog(runner)
    check_compose(runner)
    check_models(runner, metadata_only=True)
    check_training_pipeline(runner)
    check_release_registry(runner)
    return runner.finish()


def check_training_pipeline(runner: ValidationRunner) -> None:
    runner.section("Continuous Training Pipeline")
    runner.check("pipeline dvc.yaml exists", ["test", "-f", "training/pipeline/dvc.yaml"])
    runner.check("pipeline params.yaml exists", ["test", "-f", "training/pipeline/params.yaml"])
    runner.check("mlflow compose exists", ["test", "-f", "training/mlflow/docker-compose.yml"])
    runner.check("pipeline runner syntax", [sys.executable, "-m", "py_compile", "llm_local/pipeline/runner.py"])
    runner.check(
        "training pipeline unit tests",
        [sys.executable, "-m", "pytest", "tests/test_training_pipeline.py", "-q"],
    )


def check_release_registry(runner: ValidationRunner) -> None:
    runner.section("Release Registry")
    runner.check("releases package syntax", [sys.executable, "-m", "py_compile", "llm_local/releases/schema.py"])
    runner.check("releases store syntax", [sys.executable, "-m", "py_compile", "llm_local/releases/store.py"])
    runner.check("releases cli syntax", [sys.executable, "-m", "py_compile", "llm_local/releases/cli.py"])
    runner.check("releases serving syntax", [sys.executable, "-m", "py_compile", "llm_local/releases/serving.py"])
    runner.check("release registry unit tests", [sys.executable, "-m", "pytest", "tests/test_release_registry.py", "-q"])
    if not REGISTRY_COMPOSE.exists():
        print("  SKIP release registry compose workflow (registry/docker-compose.yml missing)")
        return
    docker_ok = subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    if not docker_ok:
        print("  SKIP release registry integration workflow (Docker unavailable)")
        return
    runner.check(
        "release registry integration workflow",
        compose_args(
            "-f",
            str(REGISTRY_COMPOSE),
            "run",
            "--rm",
            "--entrypoint",
            "bash",
            "release-registry",
            "/app/tests/integration/release_registry/scripts/integration-workflow.sh",
        ),
    )


def run_platform(service_id: str | None = None) -> int:
    runner = ValidationRunner()
    check_runtime(runner, service_id=service_id)
    return runner.finish()


def run_release(service_id: str | None = None) -> int:
    runner = ValidationRunner()
    check_catalog(runner)
    check_compose(runner)
    check_models(runner, metadata_only=False)
    check_scripts(runner)
    check_dashboards(runner)
    check_makefile(runner)
    check_images(runner)
    check_runtime(runner, service_id=service_id)
    return runner.finish()


def check_catalog(runner: ValidationRunner) -> None:
    runner.section("Runtime Catalog")
    runner.check_python(
        "runtime catalog loads",
        "from llm_local.catalog import load_catalog; assert load_catalog()['services']",
    )
    runner.check_python(
        "validation command registry loads",
        "from llm_local.catalog import validation_commands; assert validation_commands()",
    )


def check_compose(runner: ValidationRunner) -> None:
    runner.section("Compose Configs")
    compose_files_list = list(compose_files())
    if REGISTRY_COMPOSE.exists():
        compose_files_list.append(REGISTRY_COMPOSE)
    for compose_file in compose_files_list:
        runner.check(str(compose_file.relative_to(ROOT)), compose_args("-f", str(compose_file), "config"))


def check_models(runner: ValidationRunner, *, metadata_only: bool) -> None:
    runner.section("Model Management")
    runner.check("desired-models.yaml exists", ["test", "-f", "models/desired-models.yaml"])
    runner.check("presets.yaml exists", ["test", "-f", "models/presets.yaml"])
    runner.check("convert.sh executable", ["test", "-x", "models/convert.sh"])
    runner.check("model registry module syntax", [sys.executable, "-m", "py_compile", "llm_local/models/registry.py"])
    runner.check("model manage module syntax", [sys.executable, "-m", "py_compile", "llm_local/models/manage.py"])
    runner.check("model presets module syntax", [sys.executable, "-m", "py_compile", "llm_local/models/presets.py"])
    runner.check("desired model manifest validates", [
        sys.executable, "-m", "llm_local.models.registry", "--desired", "models/desired-models.yaml",
    ])
    if not metadata_only:
        runner.check("registry.yaml exists", ["test", "-f", "models/registry.yaml"])
        runner.check("registry files validate", [sys.executable, "-m", "llm_local.models.registry"])
    runner.check("serving presets list", [sys.executable, "-m", "llm_local.models.presets", "list"])
    runner.check(
        "serving preset dry run",
        [sys.executable, "-m", "llm_local.models.presets", "apply", "vllm-sample-chat", "--dry-run", "--render"],
    )


def check_scripts(runner: ValidationRunner) -> None:
    runner.section("Scripts")
    runner.check("convert.sh syntax", ["bash", "-n", "models/convert.sh"])
    runner.check("preflight module syntax", [sys.executable, "-m", "py_compile", "llm_local/ops/preflight.py"])
    runner.check("validate_evidence module syntax", [sys.executable, "-m", "py_compile", "llm_local/ops/validate_evidence.py"])
    runner.check(
        "llm_local package syntax",
        [
            "sh",
            "-c",
            f"{sys.executable} -m py_compile llm_local/*.py llm_local/models/*.py "
            f"llm_local/releases/*.py llm_local/pipeline/*.py llm_local/pipeline/stages/*.py "
            f"llm_local/ops/*.py",
        ],
    )
    runner.check("llm-local shim syntax", ["bash", "-n", "llm-local"])
    runner.check("run_lm_eval.sh syntax", ["sh", "-n", "evaluation/scripts/run_lm_eval.sh"])
    runner.check("evidence metadata validates", [sys.executable, "-m", "llm_local.ops.validate_evidence"])


def check_dashboards(runner: ValidationRunner) -> None:
    runner.section("Dashboards")
    runner.check_python(
        "Grafana dashboard JSON",
        "import json; from pathlib import Path; "
        "[json.loads(path.read_text()) for path in Path('observation/grafana/dashboards').glob('*.json')]",
    )
    runner.check_python(
        "Prometheus alert rules YAML",
        "from pathlib import Path; from ruamel.yaml import YAML; "
        "[YAML().load(path.read_text()) for path in Path('observation/prometheus/rules').glob('*.yml')]",
    )


def check_makefile(runner: ValidationRunner) -> None:
    runner.section("Makefile")
    runner.check("make help", ["make", "help"])


def check_images(runner: ValidationRunner) -> None:
    runner.section("Image Defaults")
    failures: list[str] = []
    for service_id, image in image_specs():
        spec = service(service_id)
        tag = str(image.get("default_tag", ""))
        if not tag:
            failures.append(f"{service_id}: missing default image tag")
        compose_file = spec.get("compose_file")
        if compose_file:
            image_value = compose_image_value(ROOT / str(compose_file), service_id, spec)
            if not image_value:
                failures.append(f"{service_id}: compose image field not found")
            else:
                repository = str(image.get("repository"))
                if repository not in image_value:
                    failures.append(f"{service_id}: compose image does not use {repository}")
                if tag and tag not in image_value:
                    failures.append(f"{service_id}: compose image does not include catalog default tag {tag}")
        env_key = image.get("tag_env")
        if env_key:
            example = service_dir(service_id) / ".env.example"
            if example.exists():
                values = parse_env_file(example)
                if env_key in values and values[env_key] != tag:
                    failures.append(
                        f"{service_id}: {example.relative_to(ROOT)} {env_key}={values[env_key]} "
                        f"does not match catalog default {tag}"
                    )
    if failures:
        for failure in failures:
            print(f"  FAIL {failure}")
            runner.failed += 1
    else:
        print("  PASS runtime catalog image defaults match compose and examples")
        runner.passed += 1


def compose_image_value(compose_file: Path, service_id: str, spec: dict[str, object]) -> str | None:
    data = YAML().load(compose_file.read_text()) or {}
    services = data.get("services") or {}
    candidates = [service_id, str(spec.get("container") or ""), service_id.replace(".", "-")]
    for candidate in candidates:
        if candidate and candidate in services:
            image = services[candidate].get("image")
            return str(image) if image else None
    return None


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def check_runtime(runner: ValidationRunner, service_id: str | None = None) -> None:
    runner.section("Runtime Network")
    runner.check(f"{network_name()} exists", ["docker", "network", "inspect", network_name()])

    runner.section("Runtime Guardrails")
    if service_id:
        runner.check(f"{service_id} guardrails pass", [sys.executable, "-m", "llm_local.ops.preflight", service_id])
    else:
        runner.check("guardrails pass", [sys.executable, "-m", "llm_local.ops.preflight", "--all"])

    runner.section("Runtime Health")
    services_to_check = [service_id] if service_id else runtime_check_services()
    for current_service_id in services_to_check:
        spec = service(current_service_id)
        if not spec.get("runtime_check"):
            print(f"  SKIP {current_service_id} has no runtime_check")
            continue
        check = spec.get("runtime_check") or {}
        container = spec.get("container")
        required = bool(check.get("required")) or bool(service_id)
        healthy_states = set(check.get("healthy_states") or ["healthy", "running"])
        if container:
            shell = (
                f"docker inspect {container} >/dev/null 2>&1"
                + ("" if required else " || exit 0")
                + f"; status=$(docker inspect --format='{{{{if .State.Health}}}}{{{{.State.Health.Status}}}}{{{{else}}}}{{{{.State.Status}}}}{{{{end}}}}' {container} 2>/dev/null); "
                + 'case "$status" in '
                + "|".join(sorted(healthy_states))
                + ") exit 0 ;; *) exit 1 ;; esac"
            )
            runner.check(f"{current_service_id} health", ["sh", "-c", shell])

        endpoint = check.get("host_endpoint")
        if endpoint:
            port = host_port(current_service_id)
            if port is not None:
                url = str(endpoint).format(host_port=port)
                shell = f"curl -sf {json.dumps(url)}" + ("" if required else " >/dev/null 2>&1 || exit 0")
                runner.check(f"{current_service_id} endpoint", ["sh", "-c", shell])


def parse_service_arg(args: list[str]) -> str | None:
    if "--service" not in args:
        return None
    index = args.index("--service")
    if index + 1 >= len(args):
        print("ERROR: --service requires a service id")
        raise SystemExit(1)
    service_id = args[index + 1]
    if service_id not in service_ids():
        print(f"ERROR: unknown service '{service_id}'. Choose from: {', '.join(service_ids())}")
        raise SystemExit(1)
    return service_id


def print_registry() -> int:
    commands = validation_commands()
    print("Validation commands:")
    for name, spec in commands.items():
        print(f"  {name}: {spec.get('command')} ({spec.get('ladder_level')})")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    command = args.pop(0) if args else "quick"
    if command == "quick":
        include_runtime = "--runtime" in args
        return run_quick(include_runtime=include_runtime)
    if command == "integration":
        return run_integration()
    if command == "platform":
        return run_platform(service_id=parse_service_arg(args))
    if command == "release":
        return run_release(service_id=parse_service_arg(args))
    if command == "images":
        runner = ValidationRunner()
        check_images(runner)
        return runner.finish()
    if command == "list":
        return print_registry()
    print("Usage: python -m llm_local.validation [quick|integration|platform|release|images|list] [--runtime]")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
