"""Model lifecycle commands: list, rm, select."""

import os
import shutil
import sys
from ruamel.yaml import YAML

from llm_local.catalog import ROOT, format_targets, runtime_env_map
from llm_local.compose import compose_args
from llm_local.models.paths import MODELS_DATA_DIR, REGISTRY_FILE
from llm_local.models.registry import assemble, model_targets

yaml = YAML()
yaml.default_flow_style = False

MODELS_DIR = str(MODELS_DATA_DIR)
ROOT_DIR = str(ROOT)


def load_registry():
    path = str(REGISTRY_FILE)
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        data = yaml.load(f)
    return (data or {}).get("models", [])


def has_target(model, target):
    return target in model_targets(model)


def list_models():
    models = load_registry()
    if not models:
        print("No local model inventory registered.")
        print("Run `./llm-local model validate` after downloading models.")
        return
    print(f"{'ID':30s} {'FORMAT':12s} {'SIZE':8s} {'TARGETS':28s} STATUS")
    for m in models:
        targets = ",".join(model_targets(m)) or "?"
        print(f"{m['id']:30s} {m.get('format','?'):12s} "
              f"{str(m.get('size_gb','?'))+' GB':8s} "
              f"{targets:28s} {m.get('status','?')}")


def rm_model(model_id, force=False):
    model_dir = os.path.join(MODELS_DIR, model_id)
    if not os.path.isdir(model_dir):
        print(f"Model directory not found: {model_dir}")
        sys.exit(1)

    if not force:
        answer = input(f"Remove {model_id} and all its files? [y/N] ")
        if answer.lower() != "y":
            print("Aborted.")
            return

    shutil.rmtree(model_dir)
    print(f"[+] Removed {model_dir}")

    assemble()


RUNTIME_ENV_MAP = runtime_env_map()
FORMAT_TARGETS = format_targets()
FORMAT_EXTENSIONS = [
    ("gguf", ".gguf"),
    ("safetensors", ".safetensors"),
    ("pytorch", ".bin"),
]


def path_has_separator(value):
    return os.sep in value or (os.altsep is not None and os.altsep in value)


def normalize_local_path(value):
    """Resolve registry-id-like and path-like input to a local model path."""
    expanded = os.path.expanduser(value)
    candidates = []
    if os.path.isabs(expanded):
        candidates.append(expanded)
    else:
        if path_has_separator(expanded):
            candidates.append(os.path.join(ROOT_DIR, expanded))
        candidates.append(os.path.join(MODELS_DIR, expanded))

    for candidate in candidates:
        abs_path = os.path.abspath(candidate)
        if os.path.exists(abs_path):
            return abs_path
    return None


def relative_to_root(abs_path):
    return os.path.relpath(abs_path, ROOT_DIR).replace(os.sep, "/")


def relative_to_models(abs_path):
    rel = os.path.relpath(abs_path, MODELS_DIR)
    if rel == "." or rel.startswith("..") or os.path.isabs(rel):
        return None
    return rel.replace(os.sep, "/")


def container_model_path(path):
    abs_path = path if os.path.isabs(path) else os.path.join(ROOT_DIR, path)
    rel = relative_to_models(os.path.abspath(abs_path))
    if rel is None:
        return None
    return f"/models/{rel}"


def gguf_files(model_path):
    if os.path.isfile(model_path) and model_path.endswith(".gguf"):
        return [model_path]
    if not os.path.isdir(model_path):
        return []
    return [
        os.path.join(model_path, name)
        for name in sorted(os.listdir(model_path))
        if name.endswith(".gguf")
    ]


def mmproj_files(model_path):
    files = gguf_files(model_path if os.path.isdir(model_path) else os.path.dirname(model_path))
    return [
        path for path in files
        if "mmproj" in os.path.basename(path).lower()
    ]


def quant_label(path):
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    labels = [
        "q8_0",
        "q6_k",
        "q5_k_m",
        "q5_k_s",
        "q4_k_m",
        "q4_k_s",
        "q3_k_m",
        "q2_k",
        "bf16",
        "f16",
        "f32",
    ]
    return next((label for label in labels if stem.endswith(label)), "")


def default_mmproj(model_path, primary_path=None):
    candidates = mmproj_files(model_path)
    if not candidates:
        return ""
    primary_quant = quant_label(primary_path or model_path)
    if primary_quant:
        matching = [
            path for path in candidates
            if quant_label(path) == primary_quant
        ]
        if len(matching) == 1:
            return matching[0]
    f16 = [
        path for path in candidates
        if "f16" in os.path.basename(path).lower()
    ]
    if len(f16) == 1:
        return f16[0]
    if len(candidates) == 1:
        return candidates[0]
    return ""


def primary_gguf(model_path):
    files = gguf_files(model_path)
    if not files:
        return None
    primary = [
        path for path in files
        if "mmproj" not in os.path.basename(path).lower()
    ]
    if len(primary) == 1:
        return primary[0]
    if len(files) == 1:
        return files[0]
    print("ERROR: multiple GGUF model files found; pass the desired .gguf file explicitly:")
    for path in files:
        print(f"  {path}")
    sys.exit(1)


def detect_format(model_path, runtime):
    if runtime in FORMAT_TARGETS.get("gguf", set()):
        gguf = primary_gguf(model_path)
        if gguf:
            return "gguf", gguf

    if os.path.isfile(model_path):
        for fmt, ext in FORMAT_EXTENSIONS:
            if model_path.endswith(ext):
                return fmt, model_path
        return "", model_path

    for fmt, ext in FORMAT_EXTENSIONS:
        if any(name.endswith(ext) for name in os.listdir(model_path)):
            return fmt, model_path
    return "", model_path


def local_model_id(model_path, selected_path):
    if os.path.isdir(model_path):
        return os.path.basename(os.path.normpath(model_path))
    parent = os.path.dirname(selected_path)
    if relative_to_models(parent) is not None and parent != MODELS_DIR:
        return os.path.basename(parent)
    return os.path.splitext(os.path.basename(selected_path))[0]


def resolve_local_model(model_id, runtime):
    model_path = normalize_local_path(model_id)
    if not model_path:
        return None

    if relative_to_models(model_path) is None:
        print(f"ERROR: local model path must be under {MODELS_DIR}: {model_path}")
        sys.exit(1)

    fmt, selected_path = detect_format(model_path, runtime)
    if not fmt:
        print(f"ERROR: local model path has no supported model files: {model_path}")
        sys.exit(1)

    compatible_targets = FORMAT_TARGETS.get(fmt)
    if compatible_targets is not None and runtime not in compatible_targets:
        allowed = ", ".join(sorted(compatible_targets))
        print(
            f"ERROR: local model path '{model_id}' format '{fmt}' "
            f"is not compatible with {runtime}. Allowed runtime(s): {allowed}"
        )
        sys.exit(1)

    model_dir = model_path if os.path.isdir(model_path) else os.path.dirname(selected_path)
    mmproj = default_mmproj(model_dir, selected_path)
    entry = {
        "id": local_model_id(model_path, selected_path),
        "repo": f"local/{local_model_id(model_path, selected_path)}",
        "format": fmt,
        "size_gb": round(os.path.getsize(selected_path) / (1024 ** 3), 1)
        if os.path.isfile(selected_path)
        else "?",
        "path": relative_to_root(selected_path if fmt == "gguf" else model_path),
        "serving_targets": sorted(compatible_targets or [runtime]),
        "quantizations": [],
        "status": "local",
    }
    if mmproj:
        entry["mmproj_path"] = relative_to_root(mmproj)
    return entry


def resolve_model(model_id, runtime="vllm"):
    if runtime not in RUNTIME_ENV_MAP:
        print(f"ERROR: unknown runtime '{runtime}'. Choose from: {', '.join(RUNTIME_ENV_MAP)}")
        sys.exit(1)

    models = load_registry()
    match = next((m for m in models if m["id"] == model_id and has_target(m, runtime)), None)
    if not match:
        match = resolve_local_model(model_id, runtime)
    if not match:
        print(f"Model '{model_id}' not found or not targeted for {runtime}.")
        print("Available:")
        for m in models:
            if has_target(m, runtime):
                print(f"  {m['id']}")
        sys.exit(1)

    compatible_targets = FORMAT_TARGETS.get(match.get("format", ""))
    if compatible_targets is not None and runtime not in compatible_targets:
        allowed = ", ".join(sorted(compatible_targets))
        print(
            f"ERROR: model '{model_id}' format '{match.get('format')}' "
            f"is not compatible with {runtime}. Allowed runtime(s): {allowed}"
        )
        sys.exit(1)

    return match


def selection_values(match):
    model_path = match["path"]
    container_path = container_model_path(model_path)
    if container_path is None:
        print(f"ERROR: model path must be under models/: {model_path}")
        sys.exit(1)

    mmproj_path = match.get("mmproj_path", "")
    if not mmproj_path:
        path_abs = model_path if os.path.isabs(model_path) else os.path.join(ROOT_DIR, model_path)
        candidate = default_mmproj(path_abs, path_abs if os.path.isfile(path_abs) else None)
        if candidate:
            mmproj_path = relative_to_root(candidate)

    mmproj_container_path = container_model_path(mmproj_path) if mmproj_path else ""
    return {
        "name": os.path.basename(os.path.normpath(model_path)),
        "repo": match["repo"],
        "path": model_path,
        "container_path": container_path,
        "mmproj_path": mmproj_path,
        "mmproj_container_path": mmproj_container_path or "",
    }


def select_model(model_id, runtime="vllm", restart=False):
    match = resolve_model(model_id, runtime=runtime)
    cfg = RUNTIME_ENV_MAP[runtime]
    env_dir = os.path.join(ROOT_DIR, cfg["dir"])
    env_file = os.path.join(env_dir, ".env")

    # Create .env from .env.example if missing
    if not os.path.isfile(env_file):
        example = os.path.join(env_dir, ".env.example")
        if os.path.isfile(example):
            import shutil as _shutil
            _shutil.copy2(example, env_file)
        else:
            print(f"[!] {env_file} not found.")
            sys.exit(1)

    with open(env_file) as f:
        lines = f.readlines()

    values = selection_values(match)
    replacements = {
        k: v.format(**values)
        for k, v in cfg["keys"].items()
    }

    new_lines = []
    existing = set()
    for line in lines:
        key = line.split("=")[0].strip()
        if key in replacements:
            new_lines.append(f"{key}={replacements[key]}\n")
            existing.add(key)
        else:
            new_lines.append(line)
    for key, value in replacements.items():
        if key not in existing:
            new_lines.append(f"{key}={value}\n")

    with open(env_file, "w") as f:
        f.writelines(new_lines)
    print(f"[+] Selected {match['id']} for {runtime}")

    if restart:
        import subprocess
        subprocess.run(compose_args("up", "-d"), cwd=env_dir)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        list_models()
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "list":
        list_models()
    elif cmd == "rm":
        if len(sys.argv) < 3:
            print("Usage: manage.py rm <model_id>")
            sys.exit(1)
        force = "--force" in sys.argv
        rm_model(sys.argv[2], force=force)
    elif cmd == "select":
        if len(sys.argv) < 3:
            print("Usage: manage.py select <model_id> [--runtime RUNTIME] [--restart]")
            sys.exit(1)
        restart = "--restart" in sys.argv
        runtime = "vllm"
        if "--runtime" in sys.argv:
            idx = sys.argv.index("--runtime")
            if idx + 1 < len(sys.argv):
                runtime = sys.argv[idx + 1]
        select_model(sys.argv[2], runtime=runtime, restart=restart)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
