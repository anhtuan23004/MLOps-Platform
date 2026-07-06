#!/usr/bin/env python3
"""Add positions and ICD-10/RxNorm candidates to three-field predictions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from llm_local.catalog import ROOT
from llm_local.ontology.medical_enrichment import (
    enrich_entities,
    load_icd10,
    load_rxnorm,
    validate_enriched,
)


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def display_path(path: Path) -> str:
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("data/input"))
    parser.add_argument(
        "--prediction-dir",
        type=Path,
        default=Path("training/pipeline/evaluation/predictions"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("training/pipeline/evaluation/submission-output"),
    )
    parser.add_argument(
        "--icd10",
        type=Path,
        default=Path("data/ontology/icd10-vn/icd10-tt06-vi.jsonl"),
    )
    parser.add_argument(
        "--rxnorm",
        type=Path,
        default=Path("data/ontology/rxnorm/2026-06-01/rxnorm-concepts.jsonl"),
    )
    parser.add_argument("--candidate-limit", type=int, default=5)
    args = parser.parse_args(argv)
    if args.candidate_limit < 1:
        parser.error("--candidate-limit must be positive")

    input_dir = resolve(args.input_dir)
    prediction_dir = resolve(args.prediction_dir)
    output_dir = resolve(args.output_dir)
    sources = {path.stem: path for path in input_dir.glob("*.txt")}
    predictions = {path.stem: path for path in prediction_dir.glob("*.json")}
    if sources.keys() != predictions.keys():
        missing = sorted(sources.keys() - predictions)
        unexpected = sorted(predictions.keys() - sources)
        raise ValueError(f"prediction coverage mismatch: missing={missing}, unexpected={unexpected}")

    icd10 = load_icd10(resolve(args.icd10))
    rxnorm = load_rxnorm(resolve(args.rxnorm))
    output_dir.mkdir(parents=True, exist_ok=True)
    stale = sorted(path.name for path in output_dir.glob("*.json") if path.stem not in sources)
    if stale:
        raise ValueError(f"output directory contains unexpected JSON files: {stale}")
    entity_count = candidate_count = 0
    for name in sorted(sources):
        source = sources[name].read_text()
        entities = json.loads(predictions[name].read_text())
        enriched = enrich_entities(
            source,
            entities,
            icd10=icd10,
            rxnorm=rxnorm,
            candidate_limit=args.candidate_limit,
        )
        errors = validate_enriched(source, enriched)
        if errors:
            raise ValueError(f"{name}.json: {'; '.join(errors)}")
        entity_count += len(enriched)
        candidate_count += sum(bool(entity["candidates"]) for entity in enriched)
        output = output_dir / f"{name}.json"
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(output)

    report = {
        "records": len(sources),
        "entities": entity_count,
        "entities_with_candidates": candidate_count,
        "icd10": display_path(resolve(args.icd10)),
        "rxnorm": display_path(resolve(args.rxnorm)),
        "candidate_limit": args.candidate_limit,
    }
    (output_dir.parent / "enrichment-report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
