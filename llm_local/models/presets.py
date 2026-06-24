"""Serving preset commands for workflow-level model switching."""

import os
import subprocess
import sys
from pathlib import Path

from ruamel.yaml import YAML

from llm_local.catalog import ROOT, gateway_alias, litellm_model_keys
from llm_local.compose import compose_with_env
from llm_local.config_paths import ACTIVE_SERVING_STATE, ensure_local_env
from llm_local.models.manage import (
    RUNTIME_ENV_MAP,
    path_has_separator,
    relative_to_root,
    resolve_model,
    select_model,
)
from llm_local.models.paths import PRESETS_FILE

yaml = YAML()
STATE_DIR = ACTIVE_SERVING_STATE.parent
ACTIVE_FILE = ACTIVE_SERVING_STATE

LITELLM_MODEL_KEYS = litellm_model_keys()


def load_presets():
    if not PRESETS_FILE.is_file():
        print(f"ERROR: presets file not found: {PRESETS_FILE}")
        sys.exit(1)
    with PRESETS_FILE.open() as handle:
        data = yaml.load(handle) or {}
    return data.get("presets", []) or []


def save_presets(presets):
    with PRESETS_FILE.open("w") as handle:
        yaml.dump({"presets": presets}, handle)


def find_preset(preset_id):
    for preset in load_presets():
        if preset.get("id") == preset_id:
            return preset
    print(f"ERROR: unknown serving preset '{preset_id}'. Available presets:")
    for preset in load_presets():
        print(f"  {preset.get('id')}")
    sys.exit(1)


def preset_exists(preset_id):
    return any(preset.get("id") == preset_id for preset in load_presets())


def slug(value):
    result = []
    for char in value.lower():
        if char.isalnum():
            result.append(char)
        elif result and result[-1] != "-":
            result.append("-")
    return "".join(result).strip("-")


def default_preset_id(runtime, model_name):
    local_name = Path(model_name).name if path_has_separator(model_name) else model_name
    return f"{runtime.replace('.', '-')}-{slug(local_name)}"


def model_label(preset):
    model = preset.get("model") or {}
    if isinstance(model, str):
        return model
    return model.get("id") or model.get("name") or "?"


def list_presets():
    presets = load_presets()
    if not presets:
        print("No serving presets configured.")
        return
    print(f"{'ID':20s} {'RUNTIME':12s} {'MODEL':30s} GATEWAY_ALIAS")
    for preset in presets:
        gateway = preset.get("gateway") or {}
        print(
            f"{preset.get('id','?'):20s} {preset.get('runtime','?'):12s} "
            f"{model_label(preset):30s} {gateway.get('alias','-')}"
        )


def show_preset(preset_id):
    yaml.dump(find_preset(preset_id), sys.stdout)


def preset_for_registry_model(preset_id, model_id, runtime, alias=None):
    match = resolve_model(model_id, runtime=runtime)
    model_ref = relative_to_root(model_id) if path_has_separator(model_id) else match.get("id", model_id)
    resolved_alias = alias or gateway_alias(runtime) or f"local-{runtime.replace('.', '-')}"
    return {
        "id": preset_id,
        "description": f"{model_ref} through {runtime} and the {resolved_alias} gateway alias.",
        "runtime": runtime,
        "model": {
            "type": "registry",
            "id": model_ref,
        },
        "gateway": {
            "alias": resolved_alias,
            "provider": "openai",
            "model": match.get("repo", f"local/{model_ref}"),
        },
        "requires": [runtime, "litellm"],
    }


def add_preset(args):
    runtime = "vllm"
    model_id = ""
    alias = None
    preset_id = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--from-model":
            i += 1
            model_id = args[i] if i < len(args) else ""
        elif arg == "--runtime":
            i += 1
            runtime = args[i] if i < len(args) else ""
        elif arg == "--alias":
            i += 1
            alias = args[i] if i < len(args) else ""
        elif arg == "--id":
            i += 1
            preset_id = args[i] if i < len(args) else ""
        else:
            print(f"ERROR: unknown preset add option: {arg}")
            sys.exit(1)
        i += 1

    if not model_id:
        print("ERROR: preset add requires --from-model <model-id>")
        sys.exit(1)

    preset_id = preset_id or default_preset_id(runtime, model_id)
    if preset_exists(preset_id):
        print(f"ERROR: preset already exists: {preset_id}")
        sys.exit(1)

    preset = preset_for_registry_model(preset_id, model_id, runtime, alias=alias)
    validate_preset(preset)

    presets = load_presets()
    presets.append(preset)
    save_presets(presets)
    print(f"[+] Added serving preset: {preset_id}")
    print(f"[*] Apply it with: ./llm-local preset apply {preset_id} --render")


def litellm_model_string(preset):
    gateway = preset.get("gateway") or {}
    provider = gateway.get("provider")
    model = gateway.get("model")
    if not provider or not model:
        print(f"ERROR: preset '{preset.get('id')}' needs gateway.provider and gateway.model")
        sys.exit(1)
    return f"{provider}/{model}"


def active_state_for(preset):
    gateway = preset.get("gateway") or {}
    return {
        "active": {
            "preset_id": preset.get("id"),
            "runtime": preset.get("runtime"),
            "model": preset.get("model") or {},
            "gateway": {
                "alias": gateway.get("alias"),
                "provider": gateway.get("provider"),
                "model": gateway.get("model"),
                "litellm_model": litellm_model_string(preset),
            },
        }
    }


def write_active_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with ACTIVE_FILE.open("w") as handle:
        yaml.dump(state, handle)


def load_active_state():
    if not ACTIVE_FILE.is_file():
        print(f"ERROR: active config not found: {ACTIVE_FILE}")
        print("Run: ./llm-local preset apply <id>")
        sys.exit(1)
    with ACTIVE_FILE.open() as handle:
        return yaml.load(handle) or {}


def show_active():
    yaml.dump(load_active_state(), sys.stdout)


def ensure_env_file(service_id: str):
    env_file = ensure_local_env(service_id)
    return env_file


def update_env(env_file, replacements):
    existing = set()
    new_lines = []
    for line in env_file.read_text().splitlines(keepends=True):
        key = line.split("=", 1)[0].strip()
        if key in replacements:
            new_lines.append(f"{key}={replacements[key]}\n")
            existing.add(key)
        else:
            new_lines.append(line)
    for key, value in replacements.items():
        if key not in existing:
            new_lines.append(f"{key}={value}\n")
    env_file.write_text("".join(new_lines))


def restart_compose(service_id: str):
    from llm_local.catalog import service_dir

    subprocess.run(compose_with_env(service_id, "up", "-d"), cwd=service_dir(service_id), check=True)


def validate_preset(preset):
    preset_id = preset.get("id")
    runtime = preset.get("runtime")
    if runtime not in LITELLM_MODEL_KEYS:
        print(f"ERROR: preset '{preset_id}' has unsupported runtime: {runtime}")
        sys.exit(1)

    model = preset.get("model") or {}
    if not isinstance(model, dict):
        print(f"ERROR: preset '{preset_id}' model must be a mapping")
        sys.exit(1)

    model_type = model.get("type")
    if model_type == "registry":
        model_id = model.get("id")
        if not model_id:
            print(f"ERROR: preset '{preset_id}' registry model needs model.id")
            sys.exit(1)
        resolve_model(model_id, runtime=runtime)
    elif model_type == "desired":
        if not model.get("id"):
            print(f"ERROR: preset '{preset_id}' desired model needs model.id")
            sys.exit(1)
    else:
        print(f"ERROR: preset '{preset_id}' has unsupported model.type: {model_type}")
        sys.exit(1)

    litellm_model_string(preset)


def apply_preset(preset_id, restart=False, dry_run=False, render=False):
    preset = find_preset(preset_id)
    validate_preset(preset)
    state = active_state_for(preset)

    if dry_run:
        print(f"[*] Would write active state: {ACTIVE_FILE}")
        yaml.dump(state, sys.stdout)
    else:
        write_active_state(state)
        print(f"[+] Active serving preset: {preset_id}")
        print(f"[+] Wrote {ACTIVE_FILE}")

    if render or restart:
        render_active(state=state, dry_run=dry_run)

    runtime = preset.get("runtime")
    if restart:
        if dry_run:
            print(f"[*] Would restart {runtime} and litellm")
        else:
            restart_compose(runtime)
            restart_compose("litellm")


def render_active(state=None, dry_run=False):
    if state is None:
        state = load_active_state()
    active = state.get("active") or {}
    runtime = active.get("runtime")
    if runtime not in LITELLM_MODEL_KEYS:
        print(f"ERROR: active runtime is unsupported: {runtime}")
        sys.exit(1)

    model = active.get("model") or {}
    if model.get("type") == "registry":
        model_id = model.get("id")
        if dry_run:
            print(f"[*] Would render runtime model {model_id} for {runtime}")
        else:
            select_model(model_id, runtime=runtime, restart=False)
    elif model.get("type") == "desired":
        if dry_run:
            print(f"[*] Would keep {runtime} model env on placeholder desired model {model.get('id')}")
        else:
            print(f"[*] Preset {active.get('preset_id')} references desired model {model.get('id')}; update config/env/vllm.env manually or add a concrete registry preset before startup.")

    gateway = active.get("gateway") or {}
    litellm_model = gateway.get("litellm_model")
    if not litellm_model:
        print("ERROR: active gateway.litellm_model is missing")
        sys.exit(1)
    replacements = {LITELLM_MODEL_KEYS[runtime]: litellm_model}
    if dry_run:
        print(f"[*] Would render LiteLLM env: {replacements}")
        return
    litellm_env = ensure_env_file("litellm")
    update_env(litellm_env, replacements)
    print(f"[+] Rendered LiteLLM {gateway.get('alias')} -> {litellm_model}")


def usage():
    print("Usage: presets.py <list|show|add|apply|active|render> ...")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        list_presets()
    elif cmd == "show":
        if len(sys.argv) < 3:
            usage()
            sys.exit(1)
        show_preset(sys.argv[2])
    elif cmd == "add":
        add_preset(sys.argv[2:])
    elif cmd == "apply":
        if len(sys.argv) < 3:
            usage()
            sys.exit(1)
        apply_preset(
            sys.argv[2],
            restart="--restart" in sys.argv,
            render="--render" in sys.argv,
            dry_run="--dry-run" in sys.argv,
        )
    elif cmd == "active":
        show_active()
    elif cmd == "render":
        render_active(dry_run="--dry-run" in sys.argv)
    else:
        usage()
        sys.exit(1)
