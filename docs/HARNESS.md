# Harness

The project goal is to provide a reusable operating harness that lets humans and
agents turn product intent into safe, validated work.

The app or platform is what users touch. The harness is what agents touch.

## Current Repository State

MLOps-Platform starts with inherited local model infrastructure and a blank
product harness. The inherited code is scaffold, not production proof.
`docs/product/`, `docs/ARCHITECTURE.md`, `docs/stories/backlog.md`, and
`docs/TEST_MATRIX.md` contain the current project contract and must be updated
as stories are selected.

Validation proof is tracked per story. Test matrix rows marked `implemented`
must point to story packets that capture evidence from real commands, reports,
logs, or screenshots. Rows without recorded evidence should stay `planned`.
Fresh evidence should include validation date, host/runtime context, image or
model identifiers, commands, and stale triggers when relevant.

## Mental Model

```text
Human intent
  -> Feature intake
  -> Story packet
  -> Agent work loop
  -> Product delta
  -> Validation proof
  -> Harness delta
  -> Next intent
```

Every task has two possible outputs:

1. Product delta: app code, tests, API shape, data model, infrastructure, or product docs.
2. Harness delta: docs, templates, validation expectations, backlog items, or
   decision records that make the next task easier.

## Harness v0 Scope

A blank Harness v0 includes:

- Agent entrypoint.
- Product documentation structure.
- Feature intake and risk lanes.
- Story templates.
- Decision log template.
- Validation report template.
- Test matrix placeholder.
- Harness growth backlog.

MLOps-Platform additionally includes inherited infrastructure for model
management, training, evaluation, serving, and observation. New
production behavior still enters through feature intake and story packets.

## Source Hierarchy

```text
User-provided spec or prompt
  input material for first buildout or future changes

docs/product/*
  current product contract derived from accepted input

docs/stories/*
  story-sized work packets and historical evidence

docs/TEST_MATRIX.md
  behavior-to-proof control panel

docs/decisions/*
  why the contract changed
```

Before a behavior is implemented, product docs describe intent. After a
behavior is implemented, product docs plus executable tests become the living
contract.

## Spec Lifecycle

When the human provides a new specification or initiative, treat it as input
material, not as a permanent operating manual. Use it to populate product docs,
story packets, architecture decisions, and validation expectations during that
buildout.

After the specification has been decomposed, do not keep extending it as the
living product plan. Ongoing work should update smaller product docs, stories,
test matrix rows, and decision records.

Ongoing work enters the harness as one of these input types:

- New spec.
- Spec slice.
- Change request.
- New initiative.
- Maintenance request.
- Harness improvement.

The work loop is:

```text
human intent or supplied spec
  -> classify input type
  -> update or create product contract
  -> create story packet or initiative notes when needed
  -> define validation proof
  -> implement or document the blocker
  -> update product docs, stories, test matrix, and decisions
  -> capture harness friction
```

## Growth Rule

The harness grows from friction.

When an agent is confused, repeats manual reasoning, needs a new validation
command, discovers a missing rule, or sees a recurring failure pattern, it must
either improve the harness directly or add a proposal to `HARNESS_BACKLOG.md`.

## Validation Ladder

The executable validation command registry lives in
`config/validation-commands.yaml`. The inherited default commands are:

```text
make validate-quick
  bounded static checks; should not require running model services

make test-integration
  compose/config and contract checks that do not require live model services

make test-platform
  live host validation for prepared runtime hosts

make release-check
  release validation on a prepared runtime host with selected artifacts available
```

Agents must not claim a command passes until it has been run in the current
workspace. If a command no longer matches the blank harness, update the selected
story and test matrix rather than weakening proof silently.
