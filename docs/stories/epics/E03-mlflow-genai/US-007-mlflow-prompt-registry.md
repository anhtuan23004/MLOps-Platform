# US-007 MLflow Prompt Registry for continuous training

## Status

planned

## Lane

tiny

## Product Contract

Store fine-tune / chat prompt templates in **MLflow Prompt Registry** and resolve
them in the `train` stage instead of hard-coding prompts in repo files.

## Relevant Product Docs

- `docs/product/mlflow-genai.md`
- `docs/product/continuous-training.md`

## Acceptance Criteria

- `config/pipeline/params.yaml` (or `config/mlflow-genai.yaml`) includes
  `prompt.name` and `prompt.version` (or URI) reference only
- `train` stage loads prompt from MLflow before fine-tune; logs prompt version on the run
- Document CLI/UI workflow to create and bump prompt versions
- Dry-run logs resolved prompt metadata without calling Unsloth
- TEST_MATRIX row US-007 added

## Design Notes

- One initial prompt template: `fine-tune-chat` for sample-chat-small fine-tune
- Prompt content must not be duplicated in git YAML after this story
- Optional: `./llm-local train prompt {list|show|register}` thin CLI wrapper

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Prompt resolve mock + params validation |
| Integration | Dry-run train records prompt version in run_manifest |
| Platform | Real train uses prompt vN from MLflow UI |
| Release | N/A |

## Harness Delta

- `config/mlflow-genai.yaml` prompt section
- Update `docs/product/mlflow-genai.md` prompt workflow

## Evidence

<!-- evidence-metadata
validated_at:
host_type:
commands:
stale_when:
- prompt name/version in params changes
-->

Pending.
