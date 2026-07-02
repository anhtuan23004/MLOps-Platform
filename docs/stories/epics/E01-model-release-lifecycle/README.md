# E01 — Model release lifecycle

## Goal

Define the shared lifecycle and promotion contract for model releases, then wire
that contract into a usable release registry and serving promotion workflow.

## Scope

| In scope | Out of scope |
| --- | --- |
| Stage taxonomy from data prep through monitoring | Replacing the local model inventory |
| Durable release metadata and promotion states | Artifact storage redesign beyond current release files |
| Promotion and rollback gates per environment | Automated approval policy engine |
| CLI-driven serving apply and rollback flow | Multi-runtime orchestration beyond vLLM + LiteLLM |

## Stories (implementation order)

| ID | Title | Depends on |
| --- | --- | --- |
| [US-001](US-001-define-promotion-lifecycle.md) | Define promotion lifecycle | none |
| [US-002](US-002-release-registry-cli.md) | Release registry CLI + real serving promotion | US-001 |

## Product contract

- `docs/product/model-release-lifecycle.md`
- `docs/product/model-releases.md`
- `docs/runbooks/release-promotion-vm.md`

## Architecture note

```text
Lifecycle contract → release registry metadata → promote/rollback gates
  → serving alias update → vLLM runtime exposure → rollback preserved
```
