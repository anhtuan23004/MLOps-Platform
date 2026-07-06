# US-019 Deterministic ICD-10/RxNorm final-output enrichment

## Status

in_progress

## Lane

normal with stronger validation

## Product Contract

Convert three-field model predictions into the five-field competition output
without changing the model, prompt, training pipeline, serving path, or release
registry. Character positions are derived from exact source text. Diagnosis and
drug candidates come from pinned local ICD-10 and RxNorm snapshots.

The resulting candidates are retrieval suggestions, not ground truth or
clinical coding decisions.

## Relevant Product Docs

- `docs/product/medical-concept-retrieval.md`
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- A standalone command reads all source and three-field prediction files.
- Every output entity contains exactly `text`, `type`, `position`, `assertions`,
  and `candidates`.
- `position` is end-exclusive and resolves exactly to `text`.
- Diagnoses receive ranked Vietnamese ICD-10 candidate strings.
- Drugs receive ranked RxCUI strings from a pinned NLM RxNorm snapshot.
- Other entity types receive `"candidates": []`.
- Missing vocabulary files, missing predictions, non-source spans, or invalid
  final fields fail clearly.
- Vocabulary provenance includes version, source, record count, and checksum.
- Candidate misses remain empty and visible; no model or external API fabricates
  a replacement code during enrichment.
- The command remains separate from CT evaluation until organizer rules confirm
  the ICD edition, RxNorm snapshot, offset convention, and candidate limit.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Normalization, exact offsets, ICD/RxNorm lookup, final schema failures |
| Integration | Fixture input + predictions produce valid five-field output |
| E2E | Deferred until real public predictions exist |
| Platform | Not applicable |
| Release | Organizer contract decisions remain open |

## Harness Delta

Adds one isolated enrichment story and one test-matrix row. It does not modify
the CT stage or claim model-quality proof.

## Evidence

Validated 2026-07-06 on local Darwin arm64 with Python 3.13.11:

- `.venv/bin/python -m pytest tests/test_icd10_tree.py tests/test_medical_enrichment.py -q`: 13 passed.
- `make validate-quick`: 29 passed, 0 failed.
- `.venv/bin/python -m pytest -q`: 48 passed after allowing access to the configured DVC cache outside the workspace.
- ICD Vietnamese, ICD bilingual, and RxNorm snapshot row counts and checksums matched their manifests.

Status remains `in_progress` because organizer contract decisions remain open.
