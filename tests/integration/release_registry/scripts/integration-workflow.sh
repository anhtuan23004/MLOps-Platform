#!/usr/bin/env bash
set -euo pipefail

REGISTRY_ROOT="${RELEASE_REGISTRY_ROOT:-/data}"
export RELEASE_REGISTRY_ROOT="$REGISTRY_ROOT"

CLI=(python -m llm_local.releases.cli --registry-root "$REGISTRY_ROOT")

echo "=== Release registry integration workflow (metadata only) ==="

"${CLI[@]}" create \
  --id rel-integration-a \
  --name "Integration A" \
  --source model-a \
  --datasets train=ds-train-a,val=ds-val-a,test=ds-test-a \
  --config-ref training/unsloth/configs/README.md

"${CLI[@]}" attach-eval rel-integration-a --ref evaluation/results/a.json
"${CLI[@]}" submit rel-integration-a
"${CLI[@]}" approve rel-integration-a --by integration
"${CLI[@]}" promote rel-integration-a --to dev --no-apply-serving

"${CLI[@]}" create \
  --id rel-integration-b \
  --name "Integration B" \
  --source model-b \
  --datasets train=ds-train-b,val=ds-val-b,test=ds-test-b \
  --config-ref training/unsloth/configs/README.md

"${CLI[@]}" attach-eval rel-integration-b --ref evaluation/results/b.json
"${CLI[@]}" submit rel-integration-b
"${CLI[@]}" approve rel-integration-b --by integration
"${CLI[@]}" promote rel-integration-b --to dev --no-apply-serving

"${CLI[@]}" rollback --env dev --no-apply-serving
"${CLI[@]}" validate

echo "=== Integration workflow complete ==="
