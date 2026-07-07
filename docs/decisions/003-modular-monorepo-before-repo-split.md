# ADR-003: Modular Monorepo Before Repository Split

Date: 2026-07-07

## Status

Accepted

## Context

MLOps-Platform currently combines the operator control plane, runtime workload
definitions, product contracts, validation harness, local datasets, model
artifacts, and domain-specific medical utilities in one repository.

The repository is still small enough that splitting it would add release,
versioning, dependency, and coordination work before there is evidence that
separate teams or deployment cycles need it. The real architecture need is
clear ownership between folders so a future split is mechanical instead of a
rewrite.

## Decision

Keep one repository and organize it as a modular monorepo.

The stable seams are:

- `llm_local/`: Python control plane and programmatic interfaces.
- `config/`: operator-tunable product and runtime configuration.
- `training/`, `serving/`, `evaluation/`, `observation/`: workload definitions
  and runtime assets, not shared business logic.
- `docs/`: product contracts, stories, decisions, validation expectations, and
  runbooks.
- `data/` and `models/`: local state, datasets, release records, and weights;
  durable product truth belongs in manifests, release records, DVC, MLflow, and
  docs.
- `tests/`: proof for control-plane interfaces and workload contracts.

Only split into separate repositories when a folder has a different owner,
release cadence, access boundary, or CI/deployment lifecycle.

## Alternatives Considered

1. Split immediately into control-plane, runtime-infra, product-contracts, and
   domain-data repositories.
2. Keep the current layout without naming ownership boundaries.
3. Move workload folders under a new `workloads/` parent now.

## Consequences

Positive:

- Keeps local development and validation simple.
- Preserves current imports, runbooks, and validation commands.
- Makes future extraction a packaging decision instead of an architecture
  discovery exercise.

Tradeoffs:

- Folder ownership must be enforced by review and docs until tooling exists.
- A future repository split will still require CI, release, and artifact
  publishing work.
- Workload folders remain top-level for compatibility even though they form one
  conceptual runtime layer.

## Follow-Up

- Keep business logic in `llm_local/`; do not add shared Python logic under
  workload folders.
- Add new top-level folders only when they map to a stable ownership seam.
- Revisit repository split when control plane, runtime infrastructure, or
  medical domain assets need independent release cycles.
