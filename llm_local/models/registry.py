"""Assemble and validate the local model inventory."""

from __future__ import annotations

import os
import sys

from ruamel.yaml import YAML

from llm_local.catalog import ROOT, format_targets
from llm_local.models.paths import DESIRED_MODELS_FILE, MODELS_DATA_DIR, REGISTRY_FILE

yaml = YAML()
yaml.default_flow_style = False

FORMAT_GLOBS = {"safetensors": ".safetensors", "pytorch": ".bin"}
VALID_TARGETS = {"vllm"}
FORMAT_TARGETS = format_targets()
DESIRED_REQUIRED_FIELDS = {"id", "repo", "format", "serving_targets"}

HEADER = (
    "# Local Model Inventory - MLOps-Platform\n"
    "# Auto-generated from ignored per-model sidecar files.\n"
    "# Product-level model intent lives in models/desired-models.yaml.\n\n"
)


def model_targets(model: dict) -> list:
    targets = model.get("serving_targets")
    if isinstance(targets, list) and targets:
        return targets
    legacy = model.get("serving_target")
    return [legacy] if legacy else []


def normalize_model(data: dict) -> dict:
    targets = data.get("serving_targets")
    legacy_target = data.get("serving_target")
    if (not isinstance(targets, list) or not targets) and legacy_target:
        data["serving_targets"] = [legacy_target]
    data.pop("serving_target", None)
    return data


def collect_sidecars(base_dir: os.PathLike | str) -> list[dict]:
    base = str(base_dir)
    models = []
    for entry in sorted(os.listdir(base)):
        sidecar = os.path.join(base, entry, "model.yaml")
        if os.path.isfile(sidecar):
            with open(sidecar) as handle:
                data = yaml.load(handle)
            if data:
                models.append(normalize_model(data))
    return models


def assemble(base_dir: os.PathLike | str | None = None) -> None:
    base = str(base_dir or MODELS_DATA_DIR)
    models = collect_sidecars(base)
    registry_path = os.path.join(base, "registry.yaml")
    with open(registry_path, "w") as handle:
        handle.write(HEADER)
        yaml.dump({"models": models}, handle)
    print(f"[+] Wrote {registry_path} with {len(models)} model(s)")


def validate(registry_path: os.PathLike | str | None = None, *, metadata_only: bool = False) -> int:
    path = str(registry_path or REGISTRY_FILE)
    if not os.path.isfile(path):
        print(f"ERROR: Registry not found: {path}")
        return 1

    repo_root = ROOT
    with open(path) as handle:
        data = yaml.load(handle)

    models = (data or {}).get("models", [])
    print(f"[*] Validating {len(models)} model(s) from {path}\n")
    errors = 0

    for model in models:
        mid, rel_path, fmt = model.get("id", "?"), model.get("path", ""), model.get("format", "")
        abs_path = repo_root / rel_path if not os.path.isabs(rel_path) else rel_path
        print(f"  {mid:20s} {rel_path} ... ", end="")

        if not metadata_only:
            if not os.path.isdir(abs_path):
                print("MISSING")
                errors += 1
                continue
            ext = FORMAT_GLOBS.get(fmt)
            if ext and not any(name.endswith(ext) for name in os.listdir(abs_path)):
                print(f"WARN: no {ext} files")
                errors += 1
                continue

        unknown = [t for t in model_targets(model) if t not in VALID_TARGETS]
        if unknown:
            print(f"WARN: invalid target(s): {', '.join(unknown)}")
            errors += 1
            continue

        compatible = FORMAT_TARGETS.get(fmt)
        incompatible = [t for t in model_targets(model) if compatible is not None and t not in compatible]
        if incompatible:
            allowed = ", ".join(sorted(compatible))
            print(f"WARN: {fmt} incompatible with target(s): {', '.join(incompatible)}; allowed: {allowed}")
            errors += 1
            continue

        print("OK")

    print()
    if errors:
        print(f"[-] {errors} issue(s) found.")
        return 1
    print("[+] All models validated successfully.")
    return 0


def validate_desired(manifest_path: os.PathLike | str | None = None) -> int:
    path = str(manifest_path or DESIRED_MODELS_FILE)
    if not os.path.isfile(path):
        print(f"ERROR: Desired model manifest not found: {path}")
        return 1

    with open(path) as handle:
        data = yaml.load(handle) or {}

    models = data.get("desired_models", [])
    print(f"[*] Validating {len(models)} desired model(s) from {path}\n")
    errors = 0
    seen: set[str] = set()

    for model in models:
        mid = model.get("id", "?")
        print(f"  {mid:30s} ... ", end="")
        missing = sorted(DESIRED_REQUIRED_FIELDS - set(model))
        if missing:
            print(f"WARN: missing field(s): {', '.join(missing)}")
            errors += 1
            continue
        if mid in seen:
            print("WARN: duplicate id")
            errors += 1
            continue
        seen.add(mid)

        fmt = model.get("format")
        compatible = FORMAT_TARGETS.get(fmt)
        if compatible is None:
            print(f"WARN: unknown format: {fmt}")
            errors += 1
            continue

        targets = model.get("serving_targets")
        if not isinstance(targets, list) or not targets:
            print("WARN: serving_targets must be a non-empty list")
            errors += 1
            continue

        unknown = [t for t in targets if t not in VALID_TARGETS]
        if unknown:
            print(f"WARN: invalid target(s): {', '.join(unknown)}")
            errors += 1
            continue

        incompatible = [t for t in targets if t not in compatible]
        if incompatible:
            allowed = ", ".join(sorted(compatible))
            print(f"WARN: {fmt} incompatible with target(s): {', '.join(incompatible)}; allowed: {allowed}")
            errors += 1
            continue

        print("OK")

    print()
    if errors:
        print(f"[-] {errors} issue(s) found.")
        return 1
    print("[+] Desired model manifest validated successfully.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    metadata_only = "--metadata-only" in args
    desired = "--desired" in args
    filtered = [a for a in args if a not in {"--metadata-only", "--desired"}]
    if desired:
        path = filtered[0] if filtered else str(DESIRED_MODELS_FILE)
        return validate_desired(path)
    path = filtered[0] if filtered else str(REGISTRY_FILE)
    return validate(path, metadata_only=metadata_only)


if __name__ == "__main__":
    raise SystemExit(main())
