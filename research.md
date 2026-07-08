# Research: Automated Training Data for Medical Concept Extraction

Date: 2026-07-04
Status: research proposal; no implementation selected

## Objective

Build a reproducible pipeline that automatically creates Vietnamese supervised
fine-tuning data for the medical concept extraction task. The target model emits
only `text`, `type`, and `assertions`; deterministic post-processing remains
responsible for character positions and ICD-10/RxNorm candidates.

This is a new initiative. It becomes high-risk when it uses real clinical data
or external model providers because privacy, provider behavior, dataset rights,
and reproducibility become hard gates.

## Current Repository Findings

- The current SFT contract is conversation JSONL and is already validated by
  [`llm_local/pipeline/dataset.py`](llm_local/pipeline/dataset.py).
- The existing example dataset contains 11 short examples in
  [`training/pipeline/data/examples/medical-concept-extraction.sample.jsonl`](training/pipeline/data/examples/medical-concept-extraction.sample.jsonl).
- Those examples have a median length of 48 characters. The 100 public input
  documents have a median length of 1,222 characters and a maximum of 4,428
  characters. The current examples therefore do not represent target document
  shape or difficulty.
- The public input has no ground-truth labels. It can validate file coverage and
  output structure, but it must not become training data or the quality benchmark.
- ICD-10 Vietnamese labels, ICD-10-CM codes, and the RxNorm spreadsheet already
  provide controlled terminology for diagnosis and drug scenarios.

## Research Conclusion

The recommended design is **label-first synthetic generation**:

1. Select entities, assertion flags, and a clinical-note scenario deterministically.
2. Render an initial note with markers around known entity spans.
3. Ask a teacher model to rewrite the surrounding context while preserving markers.
4. Remove markers and derive exact spans mechanically.
5. Reject schema, semantic, duplicate, privacy, and leakage failures.
6. Audit a sample manually before publishing the dataset version.

This is safer than asking one model to invent both the note and its labels. The
[Self-Instruct](https://aclanthology.org/2023.acl-long.754/) workflow supports
generation followed by filtering, while research on
[synthetic clinical NER](https://aclanthology.org/2023.eacl-main.170v2.pdf)
shows that synthetic text should be evaluated by downstream usefulness on a
gold corpus rather than fluency alone.

## Proposed Pipeline

```text
licensed sources + ICD-10 + RxNorm + scenario templates
  -> scenario sampler
  -> deterministic draft with entity markers
  -> external OpenAI/Gemini/Qwen API teacher rewrite
  -> marker removal and exact-span reconstruction
  -> schema and semantic validation
  -> duplicate, leakage, and privacy checks
  -> grouped train/validation split
  -> human audit
  -> DVC snapshot + MLflow lineage
  -> SFT training + frozen gold evaluation
```

The teacher is an external OpenAI, Gemini, or Qwen API used for offline data
generation. It is not the model submitted for inference. The submitted
inference path remains self-hosted unless the competition rules are explicitly
changed. Generated datasets and debug traces must be materialized and versioned
so reproducing training does not require calling the same provider again.

## Data Contract

### Internal generation record

Each entity owns its assertion list directly:

```json
{
  "scenario_id": "inpatient-000123",
  "template_id": "inpatient-discharge-v1",
  "seed": 123,
  "entities": [
    {
      "text": "đái tháo đường type 2",
      "type": "CHẨN_ĐOÁN",
      "assertions": ["isHistorical"]
    },
    {
      "text": "metformin 500 mg",
      "type": "THUỐC",
      "assertions": []
    }
  ]
}
```

`assertions` is always an array containing zero or more of:

- `isNegated`
- `isFamily`
- `isHistorical`

For `TÊN_XÉT_NGHIỆM` and `KẾT_QUẢ_XÉT_NGHIỆM`, `assertions` must be `[]`.
Combined context is represented as multiple array values, for example:

```json
{"text":"lao phổi","type":"CHẨN_ĐOÁN","assertions":["isNegated","isFamily"]}
```

### SFT output

The assistant target remains the existing three-field JSON array:

```json
[
  {
    "text": "đái tháo đường type 2",
    "type": "CHẨN_ĐOÁN",
    "assertions": ["isHistorical"]
  }
]
```

Positions and ontology candidates are not teacher outputs and are not LoRA
training targets.

### Assertion debug trace

Assertion traces are stored as a separate JSONL sidecar keyed by `sample_id` and
`entity_id`. They must not add fields to the three-field assistant target.

For each entity, trace all three assertion decisions so an empty
`"assertions": []` remains debuggable:

```json
{
  "sample_id": "inpatient-000123",
  "entity_id": "E0",
  "entity_text": "đái tháo đường type 2",
  "entity_type": "CHẨN_ĐOÁN",
  "decisions": [
    {
      "assertion": "isNegated",
      "outcome": "absent",
      "evidence": [],
      "reason_code": "no_negation_cue"
    },
    {
      "assertion": "isFamily",
      "outcome": "absent",
      "evidence": [],
      "reason_code": "patient_subject"
    },
    {
      "assertion": "isHistorical",
      "outcome": "present",
      "evidence": [
        {"text": "Tiền sử", "start": 0, "end": 7}
      ],
      "reason_code": "history_section"
    }
  ],
  "source": {
    "kind": "scenario",
    "template_id": "inpatient-discharge-v1",
    "rule_version": "assertion-rules-v1"
  },
  "teacher": {
    "provider": "openai",
    "model": "provider-model-id",
    "request_id": "provider-request-id"
  },
  "validator": {
    "version": "assertion-validator-v1",
    "status": "accepted"
  }
}
```

Allowed decision outcomes are:

- `present`: included in the final `assertions` list.
- `absent`: applicable to the entity type but not supported by context.
- `not_applicable`: used for test-name and test-result entities.

Store bounded reason codes and evidence spans, not hidden chain-of-thought or
free-form model reasoning. If a human overrides a decision, append reviewer,
timestamp, old outcome, new outcome, and a short reason code instead of
overwriting the original trace.

## Teacher Providers

### OpenAI external API

Use Structured Outputs with the project JSON Schema rather than free-form JSON.
OpenAI documents schema-constrained output and recommends Structured Outputs
over JSON mode when supported. Large offline jobs can use the Batch API, with a
stable `custom_id` used to join responses back to scenario IDs.

- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [OpenAI Batch API](https://platform.openai.com/docs/guides/batch/)

### Gemini external API

Gemini Structured Outputs accepts a supported subset of JSON Schema. Application
validation is still required because schema-valid output can remain semantically
wrong. Large non-interactive jobs can use the Gemini Batch API.

- [Gemini Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini Batch API](https://ai.google.dev/gemini-api/docs/batch-api)

### Qwen external API

Alibaba Cloud Model Studio exposes hosted Qwen models through its native API
and an OpenAI-compatible API. This allows the same provider adapter shape to be
reused with a different base URL, API key, and model ID. Its batch inference is
explicitly intended for workloads such as data labeling. Pin a concrete model
version when available instead of a moving `latest` alias.

- [Alibaba Cloud Model Studio](https://www.alibabacloud.com/help/en/model-studio/what-is-model-studio)
- [Qwen text generation API](https://www.alibabacloud.com/help/en/model-studio/qwen-api-reference)
- [Qwen batch inference](https://www.alibabacloud.com/help/en/model-studio/batch-inference/)

### Provider-neutral requirements

Record the following for every generated row or generation batch:

- Provider and exact model identifier.
- Prompt/template version and JSON Schema hash.
- Scenario ID, random seed, and generation parameters.
- Request ID or batch item ID.
- MLflow trace ID and assertion-sidecar path.
- Raw response hash and accepted/rejected status.
- Validator version and rejection reasons.

API keys belong in environment variables or a secret store. They must not be
written to dataset metadata, DVC, MLflow artifacts, logs, or Git.

## Model Research: GLiNER and Qwen

### GLiNER

[GLiNER](https://github.com/urchade/GLiNER) is an Apache-2.0, BERT-like
bidirectional model family for zero-shot and fine-tuned named-entity
recognition. Unlike an autoregressive LLM, it predicts spans and entity labels
in parallel. The project supports CPU inference, quantization, ONNX export, and
domain-specific fine-tuning. The original NAACL paper reports strong zero-shot
NER performance against much larger generative models.

- [GLiNER paper](https://aclanthology.org/2024.naacl-long.300/)
- [GLiNER documentation](https://urchade.github.io/GLiNER/)
- [`gliner_multi-v2.1` model card](https://huggingface.co/urchade/gliner_multi-v2.1)

The multilingual `gliner_multi-v2.1` checkpoint is approximately 0.3B
parameters and is the most relevant starting checkpoint for Vietnamese. The
biomedical GLiNER checkpoint is trained for English biomedical text, so it must
not be assumed to outperform the multilingual model on Vietnamese clinical
notes without a benchmark.

GLiNER directly covers only part of the current contract:

- Good fit: exact entity spans and the five entity types.
- Missing: `isNegated`, `isFamily`, and `isHistorical` decisions.
- Missing: direct production of the current conversation JSONL/SFT response.
- Operational concern: long documents need an evaluated chunking and overlap
  strategy, followed by deterministic span-offset reconciliation.

Recommended GLiNER roles:

1. Independent span/type verifier for API-teacher output.
2. Fast weak labeler for selecting examples that need teacher or human review.
3. Fine-tuned low-cost inference baseline, paired with a separate assertion
   classifier or deterministic assertion rules.

GLiNER should not be treated as a drop-in replacement for the current Qwen-style
three-field generative output until the assertion stage and JSON adapter exist.

### Qwen

Qwen is a better direct match for the current SFT contract because it can emit
the complete JSON array and infer assertions from document-level context.

Detailed comparison: [Qwen2.5 vs Qwen3 vs Qwen3.5 for text-only SFT](research/qwen-text-model-comparison.md).
The first experiments are text-only; vision fine-tuning is intentionally deferred.

Three self-hosted Qwen3.5 checkpoints remain below the competition limit when
the full artifact, including its vision encoder, is counted:

- [`Qwen3.5-0.8B`](https://huggingface.co/Qwen/Qwen3.5-0.8B): smoke-test model.
- [`Qwen3.5-2B`](https://huggingface.co/Qwen/Qwen3.5-2B): low-cost baseline.
- [`Qwen3.5-4B`](https://huggingface.co/Qwen/Qwen3.5-4B): Qwen3.5 family
  candidate; the official collection reports about 5B for the full artifact.

Do not select `Qwen3.5-9B`: the official collection reports about 10B for the
full artifact, and the language model's nominal 9B also fails a strict `< 9B`
rule. Start with BF16 LoRA rather than the current 4-bit QLoRA path; Unsloth's
Qwen3.5 guide warns that 4-bit fine-tuning has higher-than-normal quantization
differences.

Across text-model families, benchmark `Qwen3-8B` as the max-quality candidate,
`Qwen3-4B-Instruct-2507` as the first practical candidate, and
`Qwen2.5-7B-Instruct` as the stable JSON-focused control. Keep Qwen3.5-4B as a
BF16 LoRA challenger after the Transformers v5 path is proven.

Qwen advantages:

- Produces the complete `text`/`type`/`assertions` schema in one pass.
- Uses wider document context for family, negation, and history cues.
- Fits the existing conversation JSONL and structured-prompt contract; the
  current LoRA loader and vLLM configuration still require Qwen3.5-specific
  changes documented in the detailed research.

Qwen risks:

- Generative output can omit, normalize, or hallucinate entity text.
- Higher latency and GPU cost than GLiNER.
- JSON validity does not prove semantic or exact-span correctness.
- Teacher/student use of the same model family can hide correlated errors.

### Comparison for this project

| Criterion | GLiNER | Qwen |
| --- | --- | --- |
| Exact span/type extraction | Native strength | Must be validated after generation |
| Assertion classification | Separate stage required | Can infer in the same response |
| Current three-field JSON | Adapter required | Native SFT target |
| Long document context | Requires chunking benchmark | Native long-context processing |
| Runtime cost | Low; CPU/ONNX possible | Higher; GPU preferred |
| Fine-tuning data | Span annotations | Existing conversation JSONL |
| Best role now | Verifier, weak labeler, fast baseline | External teacher and end-to-end student |

### Recommended experiment

Evaluate four paths on the same frozen gold set:

1. Zero-shot `gliner_multi-v2.1` for span/type extraction.
2. Fine-tuned GLiNER plus deterministic assertion rules.
3. Text-only SFT matrix for Qwen3-8B, Qwen3-4B-Instruct-2507,
   Qwen2.5-7B-Instruct, and Qwen3.5-4B using the current JSON contract.
4. Hybrid: GLiNER proposes spans/types; Qwen sees only proposed spans and local
   context to assign assertions; deterministic code builds final JSON.

Compare exact-span F1 per entity type, assertion F1, invalid-output rate,
document coverage, latency, throughput, RAM/VRAM, and error overlap. Select an
architecture from measured results rather than zero-shot English benchmarks.

## Generation Strategy

### Deterministic scenario layer

Start from controlled facts rather than free-form prompts:

- Diagnosis names from Vietnamese ICD-10.
- Drug names from RxNorm, supplemented by a reviewed Vietnamese alias table.
- A curated list of symptoms, tests, units, routes, and dosage forms.
- Clinical-note templates such as admission, progress, discharge, laboratory,
  medication history, and family history.

Generate coverage across:

- All five entity types.
- Current, negated, family, historical, and combined assertion contexts.
- Empty-entity documents and hard negatives.
- Repeated mentions with different assertion contexts.
- Abbreviations, casing, punctuation, bullet lists, spacing noise, and units.
- Short sentences and multi-section documents matching the target length range.

### Teacher rewrite layer

The teacher receives a marked draft such as:

```text
Tiền sử [[E0:đái tháo đường type 2]]. Hiện dùng [[E1:metformin 500 mg]].
```

It may rewrite surrounding prose, but must preserve every marker and marked
string exactly. Any missing, duplicated, reordered, or modified marker rejects
the sample. Labels and assertions come from the scenario record, not from the
teacher's judgment.

### Optional weak supervision

For licensed, unlabeled text, independent labeling functions can combine
ontology matching, patterns, and teacher predictions. Snorkel's weak-supervision
work supports this pattern but also assumes a labeled development set and a
blind held-out set. Do not add Snorkel initially unless multiple noisy labelers
actually need conflict resolution.

- [Snorkel: rapid training data creation](https://link.springer.com/article/10.1007/s00778-019-00552-1)

## Source and Licensing Rules

- Do not train on the competition public test or generate paraphrases of it.
- Split by scenario family and source before rendering variants, preventing
  paraphrases of one case from crossing train and validation boundaries.
- ViMedNER is a relevant source candidate, but its repository does not expose a
  clear dataset license. Confirm rights before ingestion or redistribution.
- PhoNER_COVID19 permits research/education use but prohibits redistribution in
  original or modified form, so it cannot be included in a reproducibility
  bundle without separate permission.

Sources:

- [ViMedNER repository](https://github.com/tdtrinh11/ViMedNer)
- [PhoNER_COVID19 terms](https://github.com/VinAIResearch/PhoNER_COVID19)

## Privacy Rules

Real clinical records are out of scope until a separate privacy/security
contract is accepted. If they are later introduced:

1. De-identify before sending content to any teacher provider.
2. Use Vietnamese-specific recognizers for names, addresses, IDs, phone numbers,
   dates, facilities, and free-form identifiers.
3. Store raw records separately from generated/training artifacts.
4. Run leakage probes and manual privacy review before publication.

Microsoft Presidio provides PII detection and anonymization primitives, but its
default English setup is not sufficient evidence for Vietnamese clinical text.

- [Presidio text anonymization](https://microsoft.github.io/presidio/text_anonymization/)

## Quality Gates

The dataset is publishable only when:

- JSON and conversation schema validity is 100%.
- Every entity text occurs verbatim and in output order.
- Allowed entity and assertion values are 100% valid.
- Test names/results always have an empty assertion list.
- Every expected marker maps to exactly one reconstructed entity.
- Exact duplicate count is zero across splits.
- No near-duplicate or derived sample overlaps with the public test.
- Each entity type and assertion category meets an agreed minimum coverage.
- A manually reviewed sample reaches at least 95% acceptance.
- Training improves the frozen gold-set baseline; lower loss alone is not proof.

Do not use the same provider/model as generator, sole judge, and final quality
gate. Deterministic validators and a human-reviewed gold set remain independent.

## Gold Set and Active Learning

Create a small, separately authored or properly licensed gold set before scaling
synthetic generation. It must never be teacher-labeled or included in training.
Track exact-span entity F1 and assertion F1 separately.

After the first student model exists, select examples for review using:

- Invalid or truncated structured output.
- Teacher/student disagreement.
- Low confidence or unstable repeated generation.
- Rare entity/assertion combinations.
- Long or unusually formatted notes.

Clinical NER research found that active learning can reduce annotation effort,
but its benefit depends on the real annotation cost and target distribution.

- [Active learning for clinical NER](https://pmc.ncbi.nlm.nih.gov/articles/PMC4934373/)

## MLOps Integration

Publish accepted splits under the existing conversation JSONL contract. Preserve
optional row metadata for lineage. The existing preparation stage should record
row counts and checksums, while DVC versions dataset artifacts.

Each MLflow training run should log:

- Dataset ID and digest.
- DVC revision or content hash.
- Source mix and accepted/rejected counts.
- Entity/assertion distribution.
- Teacher provider/model and prompt version.
- Gold-set metrics and data-quality report.
- Assertion trace artifact path and accepted/overridden decision counts.

MLflow supports recording dataset name, digest, schema, profile, and source via
its dataset tracking APIs.

- [MLflow dataset tracking](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.data.html)

Use MLflow Tracing around generation, marker reconstruction, assertion
validation, and human override steps. MLflow provides automatic tracing for
both OpenAI and Gemini calls, capturing prompts, responses, latency, model,
token usage, and exceptions. Link the root trace to `sample_id` using a client
request ID, and attach `entity_id`, provider request ID, and decision counts as
trace metadata or tags.

- [MLflow OpenAI tracing](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/openai/)
- [MLflow Gemini tracing](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/gemini/)
- [MLflow trace concepts](https://mlflow.org/docs/latest/genai/concepts/trace/)

Because provider autologging captures prompts and responses, disable or redact
payload capture for any non-synthetic or sensitive input. The assertion sidecar
may contain only the minimum evidence text needed for debugging.

## Recommended Delivery Slices

1. **US-014 — Gold-set and annotation contract**: annotation guide, frozen gold
   data, exact-span and assertion metrics.
2. **US-015 — Deterministic generator**: scenario schema, templates, ontology
   sampling, marker reconstruction, and validation report.
3. **US-016 — External teacher adapter and assertion traces**:
   OpenAI/Gemini/Qwen batch generation, provider-neutral lineage, assertion
   sidecars, retry, and cost accounting.
4. **US-017 — Dataset publication**: grouped splitting, leakage checks, DVC
   snapshot, dataset manifest, and MLflow input logging.
5. **US-018 — Active-learning loop**: review queue from student failures and
   teacher/student disagreements.

Start with approximately 5,000 validated synthetic training examples and scale
only when frozen gold metrics improve. Quantity without independent evaluation
is not a success criterion.

## Open Decisions

- Document the competition-rule interpretation that permits external hosted
  teachers for offline data generation while keeping submitted inference
  self-hosted; the current product contract still states a broader API ban.
- Which OpenAI, Gemini, or hosted Qwen model/version wins on Vietnamese clinical
  generation quality, latency, and cost.
- Whether the organizer counts the full Qwen3.5 artifact or only its language
  backbone; the recommended 4B checkpoint remains below 9B either way.
- Who reviews the gold set and what inter-annotator agreement is required.
- Which external corpora have sufficient rights for training and redistribution.
- Required minimum coverage per entity type, assertion, and document-length bin.
