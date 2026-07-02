# Model data directory

Local model **weights** and generated inventory only. Product manifests live in
`config/models/`:

- `config/models/desired-models.yaml` — product intent
- `config/models/presets.yaml` — serving presets

Ignored local artifacts:

- `registry.yaml` — assembled inventory
- `*/model.yaml` — per-model sidecars
- `*/` — downloaded weight directories

Use `./llm-local model ...` (implementation in `llm_local/models/`).
