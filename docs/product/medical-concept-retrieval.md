# Medical Concept Retrieval

Status: draft competition contract

Source intake:
[`2026-07-02-medical-ontology-challenge.md`](../intake/2026-07-02-medical-ontology-challenge.md).

## Purpose

The medical concept retrieval pipeline converts free-form Vietnamese medical
text into structured entity predictions for round one of *Ontological
Reasoning in Medical Knowledge Retrieval*.

The pipeline must detect entity spans, classify them, attach allowed contextual
assertions, normalize diagnoses and drugs to the required vocabularies, and
produce a reproducible competition submission.

## Scope

In scope:

- Offline processing of `.txt` medical records.
- Detection of five organizer-defined entity types.
- Exact character-span extraction.
- Assertion classification for diagnoses, drugs, and symptoms.
- ICD-10 candidate generation for diagnoses.
- RxNorm candidate generation for drugs.
- Submission packaging and validation.
- Reproducible private-test execution by the organizer.

Out of scope for this contract:

- Interactive UI or online serving API.
- Changes to the platform release registry or serving aliases.
- Production clinical use or medical decision support.
- Training on identifiable clinical data without a separately approved privacy
  and security contract.
- A specific model architecture or training implementation.

## Input Contract

Round-one input is a directory containing 100 UTF-8 text files:

```text
input/
├── 1.txt
├── 2.txt
├── ...
└── 100.txt
```

Each filename stem is the record identifier and must be preserved in the output
filename. The organizer does not provide a training set.

## Entity Contract

Every prediction file is a JSON array. Each array element represents one
detected medical entity.

### Model output boundary

The fine-tuned LLM emits an intermediate JSON array where each entity contains
exactly `text`, `type`, and `assertions`. Semantic field rules live in the
English system prompt (`config/prompts/medical-concept-extraction.system.txt`);
Vietnamese entity labels are kept verbatim. A compact JSON Schema
(`config/prompts/medical-concept-extraction.schema.json`) defines structure
only. `llm_local.pipeline.medical_prompt.build_medical_extraction_system_prompt()`
assembles the prompt for training samples and inference. The model must copy
`text` verbatim and preserve entity order.

Deterministic, self-hosted enrichment adds `position` and ICD-10/RxNorm
`candidates` after model inference; those fields are not LoRA training targets.
The enrichment output always includes all five fields; unsupported entity types
use an empty `candidates` array.

| Field | Requirement |
| --- | --- |
| `text` | Required string copied exactly from the source span |
| `type` | Required closed-enum entity label |
| `position` | Required two-integer character-offset list |
| `assertions` | Required for diagnoses, drugs, and symptoms; empty when none apply |
| `candidates` | Required for every entity; ICD-10 strings for diagnoses; RxNorm strings for drugs; empty array for other types |

### Assertions

Only these assertion values are allowed:

- `isNegated` — concept is negated in the text (e.g. `"không ho"`)
- `isFamily` — concept refers to a relative, not the patient (e.g. family history phrasing)
- `isHistorical` — concept refers to past medical history (e.g. `"có tiền sử hen suyễn"`)

Assertions apply to `CHẨN_ĐOÁN`, `THUỐC`, and `TRIỆU_CHỨNG` only. When none apply,
the entity must contain `"assertions": []`. At most three distinct assertion
values may appear per entity. `TÊN_XÉT_NGHIỆM` and `KẾT_QUẢ_XÉT_NGHIỆM` always
use an empty assertions array.

Allowed `type` semantics (Vietnamese labels, English definitions in the system
prompt):

| Label | Meaning |
| --- | --- |
| `TRIỆU_CHỨNG` | Symptom name reported for the patient |
| `TÊN_XÉT_NGHIỆM` | Laboratory or diagnostic test name |
| `KẾT_QUẢ_XÉT_NGHIỆM` | Test result value (value and unit when present) |
| `CHẨN_ĐOÁN` | Diagnosis assigned to the patient |
| `THUỐC` | Medication used in treatment |

Test names and test results are separate entities with separate spans. For
example, `WBC` and `14,43` must not be combined into one entity.

### Character offsets

Offsets are character positions, not token positions. The supplied examples
are consistent with an end-exclusive convention:

```text
entity.text == source[entity.position[0]:entity.position[1]]
```

This convention is provisional until the organizer confirms it. Regardless of
the final convention, every offset must be within the source bounds and resolve
to the exact emitted `text`.

### Ontology candidates

- `CHẨN_ĐOÁN` candidates are ICD-10 codes represented as strings.
- `THUỐC` candidates are RxNorm identifiers represented as strings.
- Multiple candidates are ordered from highest to lowest confidence.
- Other entity types must include `candidates` as an empty array.

The accepted vocabulary snapshots, code variants, and candidate-count limit
remain open organizer decisions.

### Reproducible enrichment baseline

The current offline baseline uses:

- Vietnamese ICD-10 data exposed by the KCB TT06 tree, aligned with the coding
  list effective under Circular 06/2026/TT-BYT.
- NLM RxNorm `01-Jun-2026` active ingredient, brand, and semantic clinical drug
  concepts (`IN`, `MIN`, `PIN`, `BN`, `SCD`, `SBD`) fetched from the official
  RxNorm API.

Run the standalone boundary after three-field prediction:

```bash
PYTHONPATH=. .venv/bin/python scripts/enrich_medical_predictions.py
```

It writes five-field JSON files under
`training/pipeline/evaluation/submission-output/`. Exact source offsets are
computed mechanically. ICD-10/RxNorm candidates are lexical retrieval results,
not ground-truth labels or clinical coding decisions. Unmatched entities retain
`"candidates": []` for later review. The default top-five limit is provisional
until the organizer confirms candidate scoring and limits.

## Output and Submission Contract

The submitted artifact is `output.zip`. After extraction it must contain:

```text
output/
├── 1.json
├── 2.json
├── ...
└── 100.json
```

For every `N.txt`, exactly one `output/N.json` must exist. A record with no
detected entity must still produce a valid file containing `[]`.

Every submission must pass automated preflight validation for:

- Filename correspondence and completeness.
- JSON syntax and top-level array shape.
- Required fields and field types.
- Allowed entity and assertion values.
- Character-offset bounds and exact text matching.
- ICD-10/RxNorm candidate string representation.
- ZIP root and directory structure.

### Public-test evaluation

After training, the adapter runs against every `.txt` file in `data/input/` and
writes three-field intermediate predictions under
`training/pipeline/evaluation/predictions/`. The CT gate checks coverage, JSON
syntax, schema, allowed values, and whether every `text` occurs verbatim in the
source record.

The public test has no ground-truth labels. This pass cannot establish model
accuracy, precision, recall, or F1. Model-quality proof requires a labeled
held-out split or the organizer's official score.

## Execution Constraints

- Models must be self-hosted.
- Each model may contain at most 9 billion parameters.
- OpenAI, Anthropic, Google, and other hosted LLM APIs are prohibited.
- Participants provide their own compute resources.
- Public datasets, pretrained medical models, synthetic data, augmentation,
  and manually annotated seed data may be used subject to licensing and
  reproducibility requirements.

## Reproducibility Contract

The organizer may request source materials from approximately the top 15 teams
before round one ends and rerun them against private data. The reproducibility
bundle must contain:

- Data-processing, training, evaluation, and inference code.
- Training data, including synthetic and augmented data.
- Model weights.
- Pinned dependency definitions.
- Fixed random seeds.
- A detailed README with setup and execution commands.

The solution must not depend on hard-coded public outputs, developer-specific
absolute paths, personal cloud accounts, or undocumented state.

## Acceptance Criteria

1. One schema-valid JSON file is generated for every input file.
2. Every emitted `text` matches its declared character span.
3. Every type, assertion, and candidate value follows the closed contract.
4. Test names and test results are emitted separately.
5. `output.zip` passes the complete pre-submission validator.
6. A clean host can reproduce inference from the submitted README, data,
   dependencies, and weights without a prohibited hosted LLM API.
7. Evaluation results are recorded against the exact model, data, and code
   revision once the official metric is available.

## Competition Timeline

- Public test announced: 2026-07-02.
- Submission deadline: 2026-07-30.
- Submission limit: five attempts per day while the round is open.
- The eight highest-ranked teams on the public evaluation advance to round two.

## Open Decisions

- Inclusive versus end-exclusive final character offset.
- Official scoring metric and partial-credit behavior.
- ICD-10 edition and RxNorm snapshot.
- Maximum and scoring treatment of ordered candidates.
- Handling of overlapping or nested spans.
- Assertion-field behavior for test-name and test-result entities.

Implementation must not be described as competition-ready until these items
are confirmed or explicitly accepted as documented risks.
