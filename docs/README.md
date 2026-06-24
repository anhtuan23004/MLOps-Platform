# Documentation Map

This directory holds the MLOps-Platform harness and product contract.

## Main Files

- `HARNESS.md`: how humans and agents collaborate.
- `FEATURE_INTAKE.md`: how prompts become tiny, normal, or high-risk work.
- `ARCHITECTURE.md`: architecture discovery and boundary rules.
- `TEST_MATRIX.md`: living map of behavior to proof.
- `HARNESS_BACKLOG.md`: improvements discovered while working.

## Folders

- `product/`: current product truth.
- `runbooks/`: operational paths and incident procedures once stories define them.
- `stories/`: feature packets and backlog.
- `decisions/`: durable decisions and tradeoffs.
- `templates/`: reusable spec-intake, story, decision, and validation formats.

## Current State

Harness v0 is active. The repo includes inherited infrastructure, but product
truth is intentionally blank and must be rebuilt through accepted stories.

## Documentation Loop

```text
Human prompt / new spec / change request
  -> FEATURE_INTAKE
  -> docs/product/*
  -> ARCHITECTURE.md
  -> docs/stories/*
  -> TEST_MATRIX.md
  -> docs/decisions/*
  -> HARNESS_BACKLOG.md
```

Each file has one job: product docs say what must be true, architecture says
where it fits, stories say what slice moves, the test matrix says what proves
it, and decisions preserve why.
