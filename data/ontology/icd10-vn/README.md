# ICD-10 Vietnamese ↔ CDC ICD-10-CM mapping

Crawled from the KCB / White Neuron tree API and compared against
[CDC ICD-10-CM FY2027 code descriptions](../icd10cm/2027/).

Public UI (song ngữ): https://icd.kcb.vn/icd-10-tt06/icd10-tt06-dual

## Tree API

```text
GET https://ccs.whiteneuron.com/api/ICD10_TT06/root?lang=vi
GET https://ccs.whiteneuron.com/api/ICD10_TT06/childs/chapter?id=I&lang=vi
GET https://ccs.whiteneuron.com/api/ICD10_TT06/childs/section?id=A00&lang=vi
GET https://ccs.whiteneuron.com/api/ICD10_TT06/childs/type?id=A00&lang=vi
GET https://ccs.whiteneuron.com/api/ICD10_TT06/data/disease?id=A000&lang=en
```

## Crawl

Script: `scripts/crawl_icd10_vn_full.py`

### Vietnamese only (fast)

```bash
PYTHONPATH=. ICD10_REQUEST_DELAY=0.15 .venv/bin/python scripts/crawl_icd10_vn_full.py --edition tt06
```

Output: `icd10-tt06-vi.jsonl`

### Bilingual (vi + en) — one-pass tree crawl

```bash
PYTHONPATH=. ICD10_REQUEST_DELAY=0.15 .venv/bin/python scripts/crawl_icd10_vn_full.py --edition tt06 --bilingual
```

### Bổ sung EN từ file vi đã crawl

```bash
PYTHONPATH=. ICD10_REQUEST_DELAY=0.15 .venv/bin/python scripts/crawl_icd10_vn_full.py --edition tt06 --enrich-en
```

Đọc `icd10-tt06-vi.jsonl` → ghi `icd10-tt06-bilingual.jsonl`. Dùng `--resume` nếu bị gián đoạn.

Use `--resume` to continue an interrupted crawl. If the API returns HTTP 400/520 or
timeouts, **slow down** (`ICD10_REQUEST_DELAY=0.2` or higher) and re-run with
`--resume`.

## CDC crosswalk notes

VN ICD (TT06 / WHO vol.1) is coarser than ICD-10-CM FY2027. Many CM codes map only
to a VN parent code. CDC compact codes convert with `compact[:3] + '.' + compact[3:]`
(e.g. `E110` → `E11.0`).

## Recommended pipeline use

1. Extract `CHẨN_ĐOÁN` text (Vietnamese) from model output.
2. Match against crawled `icd10-tt06-bilingual.jsonl` or search VN API by text.
3. Cross-check against CDC file when CM specificity is required.
4. Emit `candidates` using **CDC code strings** for submission; attach VN label in metadata only.

## TT06 vs ICD10 Versions (Vietnam)

There are two versions of the ICD-10 Vietnamese translation included:
- `icd10-tt06-vi.jsonl`: **(Primary)** Based on Circular 06/2019/TT-BYT of the Ministry of Health of Vietnam. Contains 9,161 codes.
- `icd10-icd10-vi.jsonl`: Based on the original international ICD-10 translation. Contains 8,379 codes.

**Key differences:**
1. **Code additions:** TT06 adds 783 specific codes (72% are in Chapter M - Musculoskeletal).
2. **Terminology:** 81% of shared codes have different Vietnamese labels due to medical terminology standardization in Vietnam (e.g., "không xác định" vs "không đặc hiệu", "nhiễm trùng" vs "nhiễm khuẩn").
3. **Usage:** Always prefer the `tt06` version for systems deployed in Vietnam, as it represents the official regulatory standard.
