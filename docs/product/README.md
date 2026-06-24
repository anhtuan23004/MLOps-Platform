# Product Docs

This directory contains the current MLOps-Platform product contract.

When a user provides a new project spec or initiative, derive smaller product
contract files here instead of keeping one large spec as the living plan. Name
files by the product domains that actually exist in that spec or initiative,
for example `model-releases.md`, `evaluation.md`, `serving.md`,
`api-conventions.md`, or `operations.md`.

Do not create domain files just to fill the folder. Sparse, current product
truth is healthier than fake completeness.

## Update Rule

When behavior changes:

1. Update the affected product doc.
2. Update or create the story packet.
3. Update `docs/TEST_MATRIX.md`.
4. Record a decision if the change affects architecture, scope, risk, or a
   previously settled product rule.
