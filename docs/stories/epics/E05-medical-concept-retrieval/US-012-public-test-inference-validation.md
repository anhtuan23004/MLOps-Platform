# US-012 Public-test structured inference validation

## Status

in_progress

## Lane

normal with stronger validation

## Product Contract

After LoRA training, run the new adapter against every `.txt` record under
`data/input/`. The model emits only `text`, `type`, and `assertions`. The CT
evaluate stage validates file coverage, JSON syntax, the closed three-field
schema, allowed values, and exact source-text presence.

The public test has no labels. This stage must not report accuracy, precision,
recall, or F1. `position` and `candidates` remain downstream enrichment work.

## Relevant Product Docs

- `docs/product/medical-concept-retrieval.md`
- `docs/product/continuous-training.md`

## Acceptance Criteria

- Non-dry-run evaluation loads the adapter produced by the train stage.
- The Unsloth container reads all public inputs from `data/input/`.
- One JSON prediction file is produced per input file.
- Every model entity contains exactly `text`, `type`, and `assertions`.
- Invalid JSON, extra fields, invalid labels/assertions, missing files, and
  non-source text fail the CT gate.
- The eval report declares `ground_truth_available: false` and contains no
  fabricated accuracy metric.
- Dry-run validates orchestration with simulated empty arrays and marks itself
  as dry-run evidence, not model-quality proof.
- Evaluation paths remain repository-relative and work after relocating the
  checkout.
- A new host fails clearly when public input, prompt schema, adapter metadata,
  or adapter weights are missing.
- Platform proof records an immutable Unsloth image tag or digest; `latest` is
  not accepted as reproducibility evidence.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Prediction schema and invalid-field tests |
| Integration | Dry-run produces and validates one file per public input |
| E2E | Trained adapter produces valid three-field predictions for all 100 records |
| Platform | GPU-host run records model, adapter, image, and runtime identifiers |
| Release | Structural gate passes; quality gate waits for labels or organizer score |

## Evidence

<!-- evidence-metadata
validated_at: 2026-07-02
host_type: local, no GPU inference
commands:
- .venv/bin/python -m pytest tests/test_training_pipeline.py tests/test_us004_train.py tests/test_llm_dataset.py -q
- RELEASE_REGISTRY_ROOT=/private/tmp/mlops-medical-eval-registry ./llm-local train pipeline run --dry-run
stale_when:
- predict_structured.py changes
- evaluate.py changes
- medical extraction schema changes
- public input set changes
-->

Local proof: 19 focused tests passed. Dry-run generated and structurally
validated 100/100 prediction files with no errors. The predictions were
simulated empty arrays, so real adapter quality and GPU inference remain
unproven.
