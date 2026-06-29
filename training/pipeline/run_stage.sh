#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="${LLM_LOCAL_PYTHON:-python3}"
fi

if [ "$#" -ne 1 ]; then
  echo "usage: run_stage.sh <prepare_data|train|evaluate|register>" >&2
  exit 1
fi

cd "$ROOT"
exec "$PYTHON" -m "llm_local.pipeline.stages.$1"
