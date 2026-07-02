# Intake — Medical Ontology Challenge

Date: 2026-07-02

## Source

- User prompt: extract requirements from the round-one competition brief and
  prepare a minimal specification plan.
- Attached file: Vietnamese competition brief for *Ontological Reasoning in
  Medical Knowledge Retrieval*.
- External reference: none required for this intake.

## Classification

- Input type: new initiative.
- Lane: normal with stronger contract validation.
- Risk flags: data/output model, public submission contract, and weak proof
  while the official scoring details are unavailable.
- Hard gates: none identified for specification work. Any later use of private
  clinical data requires a separate privacy and security review.

## Project Summary

Build an offline pipeline that reads free-form Vietnamese medical text,
extracts supported medical entities, identifies contextual assertions, maps
diagnoses to ICD-10 and drugs to RxNorm, and packages predictions in the exact
format required by the competition organizer.

The round-one public test contains 100 text records and no organizer-provided
training set. The solution must be reproducible for organizer-run private
evaluation and must not depend on hosted LLM APIs.

## Candidate Product Docs

| File | Purpose | Source sections |
| --- | --- | --- |
| [`docs/product/medical-concept-retrieval.md`](../product/medical-concept-retrieval.md) | Entity, normalization, submission, and reproducibility contract | Competition brief sections 1–7 |

No additional product documents should be created until implementation scope
shows that data preparation, training, or evaluation needs a separate stable
contract.

## Candidate Epic

| Epic | Description | Status |
| --- | --- | --- |
| M07-medical-concept-retrieval | Produce reproducible span extraction, assertion classification, and ICD-10/RxNorm normalization for the competition | candidate |

Story packets are intentionally deferred until an implementation slice is
selected.

## Architecture Questions

- Runtime stack: not selected; any model must be self-hosted and no larger than
  9B parameters.
- Product surface: offline batch inference and submission validation CLI.
- Storage: local/public training data, redistributable synthetic data, model
  weights, and generated prediction artifacts.
- External providers: hosted LLM APIs are prohibited; permitted download and
  vocabulary sources still need to be selected and pinned.
- Deployment target: participant-provided compute for development and an
  organizer-controlled host for private reproduction.
- Security model: public competition data is assumed for round one; private or
  identifiable clinical data is outside the accepted scope.

## Validation Shape

| Layer | Expected proof |
| --- | --- |
| Unit | Entity schema, allowed labels/assertions, character spans, candidate formats |
| Integration | Input directory to output directory inference using representative fixtures |
| E2E | `output.zip` contains one valid JSON file per public input record |
| Platform | Clean-host setup and inference with pinned dependencies and packaged weights |
| Release | Submission preflight plus recorded public evaluation result and artifact identity |

## Open Decisions

1. Confirm whether `position[1]` is inclusive or exclusive. The examples imply
   end-exclusive slicing, but the prose does not state this directly.
2. Obtain the official evaluation metric, partial-credit rules, and treatment
   of ordered candidates.
3. Confirm the ICD-10 edition, RxNorm snapshot, accepted code variants, and
   maximum candidate count.
4. Confirm the policy for overlapping or nested entities.
5. Confirm whether `assertions` must be present for test-name and test-result
   entities or should be omitted.

## First Story Candidates

- Define and automate the submission-schema validator.
- Establish a labeled seed set and evaluation protocol without depending on
  the public test as training data.
- Implement baseline entity extraction for all five supported types.
- Add assertion classification for diagnoses, drugs, and symptoms.
- Add ICD-10 and RxNorm candidate retrieval and ranking.
- Prove clean-host reproducibility and package the final submission.

## Harness Delta

- Added one bounded product contract and one candidate initiative.
- Did not add Spec Kit scaffolding, source folders, CI, tests, or story packets.
- The existing `docs/` hierarchy remains the repository source of truth.
