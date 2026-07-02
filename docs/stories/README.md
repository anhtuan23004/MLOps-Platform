# Stories

Stories are work packets. They turn product intent into bounded implementation
and validation work.

Active and planned story packets live under `docs/stories/epics/`. Use
`docs/stories/backlog.md` as the current selection and status index.

Epic folders may also include a `README.md` that captures epic goal, scope,
story ordering, and linked product contracts.

## Normal Story

Use `docs/templates/story.md` for normal feature work.

Suggested path:

```text
docs/stories/epics/E01-domain-name/US-001-short-story-title.md
```

## High-Risk Story

Use `docs/templates/high-risk-story/` when the feature intake classifies work as
high-risk.

Suggested path:

```text
docs/stories/epics/E02-risky-domain/US-012-risky-story-title/
  execplan.md
  overview.md
  design.md
  validation.md
```

## Status Flow

```text
planned -> in_progress -> implemented
                  |
                  v
               changed
                  |
                  v
               retired
```
