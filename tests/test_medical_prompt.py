"""Tests for medical concept extraction system prompt template."""

from __future__ import annotations

import json
from pathlib import Path

from llm_local.pipeline.dataset import read_jsonl
from llm_local.pipeline.medical_prompt import (
    build_medical_extraction_system_prompt,
    load_medical_extraction_schema,
    medical_extraction_schema_json,
)


SAMPLE_PATH = Path("training/pipeline/data/examples/medical-concept-extraction.sample.jsonl")


def test_schema_has_structural_constraints_only():
    schema = load_medical_extraction_schema()
    entity = schema["items"]["properties"]
    assert "description" not in entity["type"]
    assert entity["type"]["enum"] == [
        "TRIỆU_CHỨNG",
        "TÊN_XÉT_NGHIỆM",
        "KẾT_QUẢ_XÉT_NGHIỆM",
        "CHẨN_ĐOÁN",
        "THUỐC",
    ]
    assertions = entity["assertions"]
    assert assertions["maxItems"] == 3
    assert assertions["uniqueItems"] is True


def test_system_prompt_is_english_with_vietnamese_labels():
    prompt = build_medical_extraction_system_prompt()
    assert "TRIỆU_CHỨNG" in prompt
    assert "symptom name reported for the patient" in prompt
    assert "isNegated" in prompt
    assert "không ho" in prompt
    assert "JSON Schema:" in prompt
    assert medical_extraction_schema_json() in prompt


def test_sample_jsonl_system_prompt_matches_template():
    expected = build_medical_extraction_system_prompt()
    for record in read_jsonl(SAMPLE_PATH, "conversation"):
        system = record["messages"][0]
        assert system["role"] == "system"
        assert system["content"] == expected


def test_sample_rows_still_cover_assertion_cases():
    records = read_jsonl(SAMPLE_PATH, "conversation")
    assistants = [json.loads(next(m["content"] for m in r["messages"] if m["role"] == "assistant")) for r in records]
    assertion_sets = {
        tuple(entity.get("assertions", []))
        for row in assistants
        for entity in row
        if entity.get("assertions")
    }
    assert ("isNegated",) in assertion_sets
    assert ("isFamily",) in assertion_sets
    assert ("isHistorical",) in assertion_sets
    assert ("isNegated", "isFamily") in assertion_sets
