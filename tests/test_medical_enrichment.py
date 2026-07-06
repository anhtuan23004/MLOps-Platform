"""Tests for deterministic final-output enrichment."""

from __future__ import annotations

import json
from pathlib import Path

from llm_local.ontology.medical_enrichment import (
    enrich_entities,
    load_icd10,
    load_rxnorm,
    normalize_term,
    validate_enriched,
)
from scripts import enrich_medical_predictions


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def test_normalize_term_handles_vietnamese_and_type_spelling():
    assert normalize_term("Đái tháo đường type 2") == "dai thao duong tip 2"


def test_submission_schema_requires_five_fields():
    schema = json.loads(
        Path("config/prompts/medical-concept-submission.schema.json").read_text()
    )
    assert schema["items"]["required"] == [
        "text",
        "type",
        "position",
        "assertions",
        "candidates",
    ]
    assert schema["items"]["additionalProperties"] is False


def test_enriches_exact_positions_and_ontology_candidates(tmp_path):
    icd_path = tmp_path / "icd.jsonl"
    rxnorm_path = tmp_path / "rxnorm.jsonl"
    write_jsonl(
        icd_path,
        [
            {
                "code": "I10",
                "label_vi": "Bệnh tăng huyết áp vô căn (nguyên phát)",
            },
            {"code": "I15.9", "label_vi": "Tăng huyết áp thứ phát, không xác định"},
        ],
    )
    write_jsonl(
        rxnorm_path,
        [{"rxcui": "6809", "name": "metformin", "tty": "IN"}],
    )
    source = "Chẩn đoán tăng huyết áp. Dùng metformin 500 mg."
    entities = [
        {"text": "tăng huyết áp", "type": "CHẨN_ĐOÁN", "assertions": []},
        {"text": "metformin 500 mg", "type": "THUỐC", "assertions": []},
    ]

    result = enrich_entities(
        source,
        entities,
        icd10=load_icd10(icd_path),
        rxnorm=load_rxnorm(rxnorm_path),
    )

    assert result[0]["position"] == [10, 23]
    assert result[0]["candidates"][0] == "I10"
    assert result[1]["position"] == [30, 46]
    assert result[1]["candidates"] == ["6809"]
    assert validate_enriched(source, result) == []


def test_non_ontology_entity_gets_empty_candidates(tmp_path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    result = enrich_entities(
        "Bệnh nhân sốt.",
        [{"text": "sốt", "type": "TRIỆU_CHỨNG", "assertions": []}],
        icd10=load_icd10(empty),
        rxnorm=load_rxnorm(empty),
    )
    assert result[0]["candidates"] == []


def test_validator_rejects_non_exact_position():
    entities = [
        {
            "text": "sốt",
            "type": "TRIỆU_CHỨNG",
            "position": [0, 3],
            "assertions": [],
            "candidates": [],
        }
    ]
    assert validate_enriched("Bệnh nhân sốt.", entities) == [
        "entity 0: invalid exact character position"
    ]


def test_standalone_command_writes_five_field_output(tmp_path):
    input_dir = tmp_path / "input"
    prediction_dir = tmp_path / "predictions"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    prediction_dir.mkdir()
    source = "Bệnh nhân dùng metformin."
    (input_dir / "1.txt").write_text(source)
    (prediction_dir / "1.json").write_text(
        json.dumps([{"text": "metformin", "type": "THUỐC", "assertions": []}])
    )
    icd_path = tmp_path / "icd.jsonl"
    rxnorm_path = tmp_path / "rxnorm.jsonl"
    icd_path.write_text("")
    write_jsonl(rxnorm_path, [{"rxcui": "6809", "name": "metformin", "tty": "IN"}])

    assert enrich_medical_predictions.main(
        [
            "--input-dir",
            str(input_dir),
            "--prediction-dir",
            str(prediction_dir),
            "--output-dir",
            str(output_dir),
            "--icd10",
            str(icd_path),
            "--rxnorm",
            str(rxnorm_path),
        ]
    ) == 0

    output = json.loads((output_dir / "1.json").read_text())
    assert output == [
        {
            "text": "metformin",
            "type": "THUỐC",
            "position": [15, 24],
            "assertions": [],
            "candidates": ["6809"],
        }
    ]
    assert (tmp_path / "enrichment-report.json").is_file()
