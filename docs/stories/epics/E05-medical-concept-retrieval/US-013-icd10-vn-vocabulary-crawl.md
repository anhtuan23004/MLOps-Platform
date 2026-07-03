# US-013 Reliable Vietnamese ICD-10 vocabulary crawl

## Status

implemented

## Lane

normal with stronger validation

## Product Contract

The Vietnamese ICD-10 crawler preserves a complete VI vocabulary and enriches
English labels from the KCB API without treating transient provider failures as
completed work. Resuming enrichment repairs failed or missing rows without
duplicating identifiers or replacing a valid dataset with partial output.

## Relevant Product Docs

- `docs/product/medical-concept-retrieval.md`

## Acceptance Criteria

- HTTP, connection-reset, and timeout failures use bounded retry and backoff.
- `--enrich-en --resume` retries rows with empty English labels or `fetch_error`.
- Repair writes atomically and preserves one row per VI identifier in source order.
- The final report states skipped, repaired, and remaining-error counts.
- Live crawl evidence records row count and remaining enrichment failures per edition.

## Design Notes

- Source API: `https://ccs.whiteneuron.com/api/{ICD10|ICD10_TT06}`.
- Commands: `scripts/crawl_icd10_vn_full.py --edition EDITION --enrich-en --resume`.
- Generated JSONL remains edition-specific; this story does not select the competition vocabulary snapshot.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Network errors normalize into retry; resume repairs failed rows without duplicates |
| Integration | Live TT06 repair completes with zero remaining `fetch_error` rows |
| E2E | Not applicable |
| Platform | Not applicable |
| Release | Vocabulary snapshot selection remains an open product decision |

## Harness Delta

Adds focused crawler proof to the medical-concept-retrieval test matrix.

## Evidence

<!-- evidence-metadata
validated_at: 2026-07-03
host_type: local
gpu: none
model_ids:
- none
commands:
- .venv/bin/python -m pytest tests/test_icd10_tree.py -q
- PYTHONPATH=. ICD10_REQUEST_DELAY=0.15 ICD10_MAX_ATTEMPTS=6 ICD10_RETRY_DELAY=2 .venv/bin/python scripts/crawl_icd10_vn_full.py --edition tt06 --enrich-en --resume
- .venv/bin/python - <<'PY'
import json
from pathlib import Path

path = Path('data/ontology/icd10-vn/icd10-tt06-bilingual.jsonl')
rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
print({'rows': len(rows), 'errors': sum(bool(r.get('fetch_error')) for r in rows), 'en_blank': sum(not r.get('label_en') for r in rows)})
PY
stale_when:
- scripts/crawl_icd10_vn_full.py changes
- llm_local/ontology/icd10_tree.py changes
- KCB API behavior or edition changes
-->

Focused unit proof: 6 tests passed. Live TT06 repair completed with 9,161
rows, 0 `fetch_error` rows, and 0 blank English labels. Final report:
`written: 0`, `skipped: 9161`, `repaired: 0`, `errors: 0`.
