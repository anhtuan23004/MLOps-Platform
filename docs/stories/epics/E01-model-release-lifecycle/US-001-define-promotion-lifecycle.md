# US-001 Define promotion lifecycle (docs-first)

## Status

planned

## Lane

normal

## Product Contract

Define a shared contract for MLOps stages and model promotion so that:
- The repo has one clear definition of **promotion** (what changes, what must exist, and how rollback works).
- Promotion is grounded in **durable artifacts** (release record, eval bundle, serving bundle).
- Stories can attach validation proof consistently via the harness ladder.

This story is **docs-first**: it establishes the contract and wiring. It does not
implement automation or runtime changes.

## Relevant Product Docs

- `docs/product/model-release-lifecycle.md`
- `docs/product/domains.md`
- `docs/product/overview.md`

## Acceptance Criteria

- `docs/product/model-release-lifecycle.md` exists and defines:
  - Stage taxonomy (Data preparation → Model development → Validation → Deployment → Monitoring)
  - Promotion states and environment mapping
  - Minimum artifacts required to promote
  - Canary + rollback direction
- `docs/product/domains.md` references the lifecycle doc as shared source-of-truth.
- `docs/TEST_MATRIX.md` has a row pointing to this story with status `planned`.
- `README.md` points readers at the lifecycle doc and the validation ladder (without claiming implementation).

## Design Notes

- Commands:
  - Validation ladder: `config/validation-commands.yaml` (`make validate-quick`, `make test-integration`, `make test-platform`, `make release-check`)
- Domain rules:
  - "Promotion" advances the release exposed via serving aliases.
  - "Rollback" is switching the alias back to the recorded rollback target.
  - Promotion requires durable release metadata + evaluation evidence + serving bundle pointer.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A (docs-only story) |
| Integration | N/A (docs-only story) |
| E2E | N/A (docs-only story) |
| Platform | N/A (docs-only story) |
| Release | N/A (docs-only story) |

## Harness Delta

- Added lifecycle contract doc and wired it into domain contract and test matrix.
- Established a single “promotion” vocabulary for future stories to reference.

## Evidence

<!-- evidence-metadata
validated_at: YYYY-MM-DD
host_type: local
gpu: none
image_tags:
- none
model_ids:
- none
commands:
- none (docs-only)
stale_when:
- lifecycle contract changes
-->

