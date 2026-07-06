# RxNorm 2026-06-01 compact snapshot

The generated `rxnorm-concepts.jsonl` contains active ingredient (`IN`, `MIN`,
`PIN`), brand-name (`BN`), semantic clinical drug (`SCD`), and semantic branded
drug (`SBD`) concepts fetched from the official NLM RxNorm API.
Each row contains only `rxcui`, `name`, and `tty`.

This snapshot was generated with:

```bash
PYTHONPATH=. .venv/bin/python scripts/fetch_rxnorm_snapshot.py --version 01-Jun-2026
```

`snapshot.json` records the API version, retrieval time, row count, selected
term types, and SHA-256 digest. The command intentionally fails after the live
API moves beyond `01-Jun-2026`; use the committed artifact and checksum for
reproduction. The older `data/RxNorm/*.xlsx` file is not used:
NLM does not publish RxNorm in Excel format and that local extract dates to 2017.

Source: https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html
