#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:-${DOCKERHUB_IMAGE:-}}"

if [[ -z "$IMAGE" ]]; then
  cat >&2 <<'USAGE'
Usage:
  scripts/viettel_dockerhub_push.sh <dockerhub-user-or-org>/viettel-qwen35:round1

Before running:
  docker login
USAGE
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUBMISSION_DIR="$ROOT_DIR/submission/viettel-round1"
GENERATED_COMPOSE="$SUBMISSION_DIR/docker-compose.generated.yml"

docker build --platform linux/amd64 -t "$IMAGE" "$SUBMISSION_DIR"
docker push "$IMAGE"

DOCKERHUB_IMAGE="$IMAGE" docker compose -f "$SUBMISSION_DIR/docker-compose.yml" config > "$GENERATED_COMPOSE"

cat <<EOF
Pushed: $IMAGE
Submit compose file: $GENERATED_COMPOSE
EOF
