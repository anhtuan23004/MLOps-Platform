#!/usr/bin/env bash
# models/convert.sh — Convert models between formats.
# Usage:
#   ./convert.sh hf2gguf <model-path> [--outtype f16|q8_0|...]
#
# Prerequisites:
#   hf2gguf: llama.cpp auto-cloned into vendor/llama.cpp on first use
#            Python deps installed with: uv sync --extra convert

set -euo pipefail

LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$(dirname "$0")/../vendor/llama.cpp}"

python_cmd() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    printf '%s\n' "$PYTHON_BIN"
  elif command -v uv >/dev/null 2>&1; then
    printf '%s\n' "uv run python"
  else
    printf '%s\n' "python3"
  fi
}

check_hf2gguf_python_deps() {
  local python_bin="$1"
  local missing

  missing="$($python_bin - <<'PY'
import importlib.util

missing = [
    module
    for module in ("gguf", "torch")
    if importlib.util.find_spec(module) is None
]
print(" ".join(missing))
raise SystemExit(1 if missing else 0)
PY
)" || {
    echo "ERROR: missing Python conversion dependencies: $missing"
    echo "Install them with: uv sync --extra convert"
    echo "Or set PYTHON_BIN to a Python environment that has: gguf torch"
    exit 1
  }
}

usage() {
  echo "Usage: $0 hf2gguf <model-dir> [--outtype TYPE]"
  echo ""
  echo "Commands:"
  echo "  hf2gguf <model-dir> [--outtype TYPE]   Convert HF safetensors to GGUF"
  exit 1
}

cmd_hf2gguf() {
  if [ $# -lt 1 ]; then
    echo "ERROR: missing model directory."
    usage
  fi

  local model_path="$1"; shift
  local outtype="f16"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --outtype)
        if [ $# -lt 2 ]; then
          echo "ERROR: --outtype requires a value."
          exit 1
        fi
        outtype="$2"
        shift 2
        ;;
      *) echo "Unknown option: $1"; exit 1 ;;
    esac
  done

  if [ ! -d "$model_path" ]; then
    echo "ERROR: model directory not found: $model_path"
    exit 1
  fi

  if [ ! -d "$LLAMA_CPP_DIR" ]; then
    echo "[*] Cloning llama.cpp into $LLAMA_CPP_DIR ..."
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git "$LLAMA_CPP_DIR"
  fi

  local python_bin
  python_bin="$(python_cmd)"
  check_hf2gguf_python_deps "$python_bin"

  local out_dir="${model_path%/}-gguf"
  mkdir -p "$out_dir"

  echo "[*] Converting $model_path -> $out_dir (outtype=$outtype)"
  $python_bin "$LLAMA_CPP_DIR/convert_hf_to_gguf.py" "$model_path" --outdir "$out_dir" --outtype "$outtype"

  local gguf_file
  gguf_file="$(find "$out_dir" -maxdepth 1 -name '*.gguf' | head -n 1)"
  if [ -z "$gguf_file" ]; then
    echo "ERROR: no GGUF output found in $out_dir"
    exit 1
  fi

  echo "[+] Wrote $gguf_file"

  local sidecar_path="${model_path%/}/model.yaml"
  if [ -f "$sidecar_path" ]; then
    local quant="${outtype}"
    $python_bin - <<PYEOF
import yaml
sidecar_path = "$sidecar_path"
quant = "$quant"
with open(sidecar_path) as f:
    data = yaml.load(f)
quants = data.setdefault("quantizations", [])
if quant not in quants:
    quants.append(quant)
targets = data.setdefault("serving_targets", [])
data["serving_targets"] = [target for target in targets if target == "vllm"] or ["vllm"]
data.pop("serving_target", None)
with open(sidecar_path, "w") as f:
    yaml.dump(data, f)
print(f"[+] Updated sidecar: added quantization '{quant}', targets: {data['serving_targets']}")
PYEOF
  fi
}

# --- Main ---
CMD="${1:-}"
[ -z "$CMD" ] && usage
shift

case "$CMD" in
  hf2gguf) cmd_hf2gguf "$@" ;;
  *)       usage ;;
esac
