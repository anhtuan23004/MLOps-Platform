# US-002 Release registry CLI + real serving promotion

## Status

in_progress

## Lane

normal

## Product Contract

Implement a file-based release registry with `llm-local release` commands that:

- Store promotion metadata under `data/release-registry/`
- Enforce promotion gates per `docs/product/model-releases.md`
- Apply promote/rollback to vLLM via `models/manage.py select` when `--apply-serving` is enabled
- Prove metadata workflow via registry Docker Compose integration test
- Document VM platform proof in `docs/runbooks/release-promotion-vm.md`

## Relevant Product Docs

- `docs/product/model-releases.md`
- `docs/product/model-release-lifecycle.md`
- `docs/runbooks/release-promotion-vm.md`

## Acceptance Criteria

- `llm_local/releases/` package implements schema, store, CLI, serving adapter
- `./llm-local release` subcommands wired in `llm_local/cli.py`
- `pytest tests/test_release_registry.py` passes
- `make test-integration` runs registry compose workflow
- VM runbook documents live promote/rollback proof on GPU host

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_release_registry.py` |
| Integration | `make test-integration` (includes registry compose workflow) |
| E2E | N/A |
| Platform | `make test-platform SERVICE=vllm` on prepared GPU VM (manual) |
| Release | `make release-check SERVICE=vllm` after VM promote/rollback (manual) |

## Harness Delta

- Added `docs/product/model-releases.md`
- Added `docs/runbooks/release-promotion-vm.md`
- Extended validation ladder with release registry checks

## Evidence

<!-- evidence-metadata
validated_at: 2026-06-24
host_type: local
gpu: none
image_tags:
- none (compose workflow skipped: Docker unavailable on validation host)
model_ids:
- none
commands:
- uv sync --extra test
- .venv/bin/python -m pytest tests/test_release_registry.py -q
- .venv/bin/python -m llm_local.validation integration
stale_when:
- release schema changes
- registry/docker-compose.yml changes
-->

Local proof (2026-06-24): 5/5 pytest passed; integration ladder passed with
compose workflow skipped (Docker daemon not running). VM platform proof pending
per runbook `docs/runbooks/release-promotion-vm.md`.
